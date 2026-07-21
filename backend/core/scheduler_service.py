"""NeuroOps Scheduler service.

Responsibilities:
  - Wake only the required agents (keep unused agents sleeping)
  - Execute independent tasks in parallel
  - Respect task dependencies (topological order)
  - Track execution progress
  - Retry failed tasks
  - Handle timeouts
  - Collect results
  - Return everything to the CEO Agent
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import Dict, List, Optional

from core import AgentResult, AgentState, Task, TaskStatus
from core.event_bus import event_bus
from core.storage import session_store
from agents.registry import AGENT_REGISTRY


class SchedulerService:
    """Executes a task DAG, respecting dependencies and running ready tasks in parallel."""

    def __init__(self, max_workers: int = 4, task_timeout_seconds: float = 30.0, max_retries: int = 2):
        self.max_workers = max_workers
        self.task_timeout = task_timeout_seconds
        self.max_retries = max_retries
        # Cache of instantiated agents (agent_type -> instance)
        self._agent_instances: Dict[str, object] = {}
        self._lock = threading.Lock()

    # ---- Agent lifecycle ----
    def _get_agent(self, agent_type: str):
        """Wake (instantiate) an agent only when needed."""
        with self._lock:
            if agent_type not in self._agent_instances:
                cls = AGENT_REGISTRY.get(agent_type)
                if cls is None:
                    raise ValueError(f"Unknown agent type: {agent_type}")
                instance = cls()
                self._agent_instances[agent_type] = instance
                event_bus.emit(
                    "agent:activated",
                    source=instance.agent_id,
                    message=f"Agent activated: {cls.__name__} ({cls.department})",
                    data={"agent_id": instance.agent_id, "agent_type": agent_type, "department": cls.department},
                )
                session_store.set_agent_state(instance.agent_id, AgentState.SLEEPING)
            return self._agent_instances[agent_type]

    def _sleep_unused_agents(self, active_types: set[str]):
        """Put agents not needed for the current wave back to sleep."""
        with self._lock:
            for agent_type, instance in list(self._agent_instances.items()):
                if agent_type not in active_types and instance.state != AgentState.SLEEPING:
                    instance.set_state(AgentState.SLEEPING)

    # ---- Dependency resolution ----
    def _get_ready_tasks(self, tasks: List[Task]) -> List[Task]:
        """Return tasks whose dependencies are all completed."""
        ready = []
        for t in tasks:
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RUNNING, TaskStatus.ASSIGNED):
                continue
            deps_done = all(
                session_store.get_task(dep) and session_store.get_task(dep).status == TaskStatus.COMPLETED
                for dep in t.dependencies
            )
            if deps_done:
                ready.append(t)
        return ready

    def _has_unfinished(self, tasks: List[Task]) -> bool:
        return any(t.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED) for t in tasks)

    # ---- Single task execution with timeout + retry ----
    def _run_task(self, task: Task) -> AgentResult:
        agent = self._get_agent(task.required_agent)
        task.assigned_agent = agent.agent_id
        task.status = TaskStatus.ASSIGNED
        task.started_at = datetime.utcnow()
        session_store.update_task(task.task_id, status=TaskStatus.ASSIGNED, assigned_agent=agent.agent_id, started_at=task.started_at)

        attempt = 0
        while attempt <= self.max_retries:
            attempt += 1
            task.retries = attempt - 1
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(agent.execute, task)
                    result = future.result(timeout=self.task_timeout)
                task.status = TaskStatus.COMPLETED
                task.result = result.output
                task.completed_at = datetime.utcnow()
                session_store.update_task(
                    task.task_id,
                    status=TaskStatus.COMPLETED,
                    result=result.output,
                    completed_at=task.completed_at,
                    retries=task.retries,
                )
                event_bus.emit(
                    "task:finished",
                    source="Scheduler",
                    message=f"Task {task.task_id} completed (attempt {attempt})",
                    data={"task_id": task.task_id, "agent_id": agent.agent_id, "confidence": result.confidence},
                )
                return result
            except FuturesTimeoutError:
                self._log_failure(task, f"Timeout after {self.task_timeout}s (attempt {attempt})")
                event_bus.emit("task:timeout", source="Scheduler", message=f"Task {task.task_id} timed out (attempt {attempt})")
            except Exception as exc:
                self._log_failure(task, f"Error: {exc} (attempt {attempt})")
                event_bus.emit("task:error", source="Scheduler", message=f"Task {task.task_id} error: {exc}")

            if attempt <= self.max_retries:
                event_bus.emit("task:retry", source="Scheduler", message=f"Retrying task {task.task_id} (attempt {attempt+1})")
                time.sleep(0.3)

        task.status = TaskStatus.FAILED
        session_store.update_task(task.task_id, status=TaskStatus.FAILED)
        event_bus.emit("task:failed", source="Scheduler", message=f"Task {task.task_id} failed after {attempt} attempts")
        return AgentResult(
            agent_id=agent.agent_id,
            task_id=task.task_id,
            output="",
            confidence=0.0,
            state=AgentState.FAILED,
            metadata={"error": "max retries exceeded"},
        )

    def _log_failure(self, task: Task, msg: str):
        task.logs.append(f"[{datetime.utcnow().isoformat()}] {msg}")

    # ---- DAG execution ----
    def execute(self, tasks: List[Task]) -> List[AgentResult]:
        """Execute the full task DAG, wave by wave (parallel within a wave)."""
        event_bus.emit("scheduler:started", source="Scheduler", message=f"Executing DAG with {len(tasks)} tasks")
        results: List[AgentResult] = []

        wave = 0
        while self._has_unfinished(tasks):
            ready = self._get_ready_tasks(tasks)
            if not ready:
                # Deadlock or all remaining failed
                stuck = [t for t in tasks if t.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)]
                if stuck:
                    for t in stuck:
                        t.status = TaskStatus.FAILED
                        session_store.update_task(t.task_id, status=TaskStatus.FAILED)
                        event_bus.emit("task:failed", source="Scheduler", message=f"Task {t.task_id} stuck (unresolvable deps)")
                break

            wave += 1
            active_types = {t.required_agent for t in ready}
            event_bus.emit("scheduler:wave", source="Scheduler", message=f"Wave {wave}: {len(ready)} tasks in parallel", data={"wave": wave, "tasks": [t.task_id for t in ready]})

            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                futures = {ex.submit(self._run_task, t): t for t in ready}
                for future in futures:
                    results.append(future.result())

        event_bus.emit("scheduler:completed", source="Scheduler", message=f"All tasks processed ({len(results)} results)")
        self._sleep_unused_agents(set())
        return results
