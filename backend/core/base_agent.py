"""NeuroOps base agent contract.

Every agent follows the same contract:
  - receive structured task input
  - think (optionally calling the Model Provider Layer)
  - produce structured output (AgentResult)
  - return confidence score
  - return execution logs
  - return execution time
  - emit state transitions
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import AgentResult, AgentState, Task
from core.event_bus import event_bus
from core.storage import session_store
from core.model_provider import model_manager


class BaseAgent(ABC):
    """Abstract base for all NeuroOps agents."""

    department: str = "general"
    description: str = ""
    capabilities: List[str] = []
    tools: List[str] = []
    model_preference: str = "stub"

    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id or f"{self.__class__.__name__}-{uuid.uuid4().hex[:6]}"
        self.state: AgentState = AgentState.SLEEPING
        self.workload: int = 0
        self.logs: List[str] = []

    # ---- State management (emits events) ----
    def set_state(self, new_state: AgentState, task_id: Optional[str] = None):
        old = self.state
        self.state = new_state
        session_store.set_agent_state(self.agent_id, new_state)
        self._emit_state_event(new_state, old, task_id)

    def _emit_state_event(self, new_state: AgentState, old_state: AgentState, task_id: Optional[str]):
        event_map = {
            AgentState.AVAILABLE: ("agent:available", "Available"),
            AgentState.ASSIGNED: ("agent:assigned", "Assigned"),
            AgentState.THINKING: ("agent:thinking", "Thinking"),
            AgentState.WORKING: ("agent:working", "Working"),
            AgentState.WAITING: ("agent:waiting", "Waiting"),
            AgentState.WAITING_APPROVAL: ("agent:waiting_approval", "Waiting Approval"),
            AgentState.COMPLETED: ("agent:completed", "Completed"),
            AgentState.FAILED: ("agent:failed", "Failed"),
            AgentState.SLEEPING: ("agent:sleeping", "Sleeping"),
        }
        event_type, label = event_map.get(new_state, ("agent:state", new_state.value))
        event_bus.emit(
            event_type,
            source=self.agent_id,
            message=f"{self.__class__.__name__} -> {label}",
            agent_id=self.agent_id,
            previous_state=old_state.value,
            new_state=new_state.value,
            data={
                "agent_id": self.agent_id,
                "agent_name": self.__class__.__name__,
                "department": self.department,
                "task_id": task_id,
            },
        )

    def log(self, message: str):
        line = f"[{datetime.utcnow().isoformat()}] {message}"
        self.logs.append(line)
        session_store.add_agent_log(self.agent_id, line)

    # ---- Model helper ----
    def call_model(self, system_prompt: str, user_prompt: str, **kwargs):
        """Call the configured AI model through the Model Manager."""
        self.log(f"Calling model ({model_manager.provider_name})")
        return model_manager.generate(system_prompt, user_prompt, **kwargs)

    # ---- Public execution contract ----
    def execute(self, task: Task) -> AgentResult:
        """Run the full agent lifecycle. Subclasses implement `think`."""
        self.logs = []
        self.workload += 1
        start = time.time()
        self.set_state(AgentState.THINKING, task.task_id)
        self.log(f"Task assigned: {task.title}")
        event_bus.emit(
            "agent:task_assigned",
            source=self.agent_id,
            message=f"Task assigned to {self.__class__.__name__}: {task.title}",
            agent_id=self.agent_id,
            data={"agent_id": self.agent_id, "task_id": task.task_id, "title": task.title},
        )
        try:
            self.set_state(AgentState.WORKING, task.task_id)
            output, confidence = self.think(task)
            elapsed = (time.time() - start) * 1000
            self.set_state(AgentState.COMPLETED, task.task_id)
            self.log(f"Completed in {elapsed:.1f}ms (confidence={confidence:.2f})")
            session_store.record_agent_performance(self.agent_id, True, confidence, elapsed)
            event_bus.emit(
                "agent:task_finished",
                source=self.agent_id,
                message=f"{self.__class__.__name__} finished task {task.task_id}",
                agent_id=self.agent_id,
                data={"agent_id": self.agent_id, "task_id": task.task_id, "confidence": confidence, "execution_time_ms": elapsed},
            )
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.task_id,
                output=output,
                confidence=confidence,
                logs=list(self.logs),
                execution_time_ms=elapsed,
                state=AgentState.COMPLETED,
            )
        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            self.set_state(AgentState.FAILED, task.task_id)
            self.log(f"FAILED: {exc}")
            session_store.record_agent_performance(self.agent_id, False, 0.0, elapsed)
            event_bus.emit(
                "agent:failed",
                source=self.agent_id,
                message=f"{self.__class__.__name__} failed on task {task.task_id}: {exc}",
                agent_id=self.agent_id,
                data={"agent_id": self.agent_id, "task_id": task.task_id, "error": str(exc)},
            )
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.task_id,
                output="",
                confidence=0.0,
                logs=list(self.logs),
                execution_time_ms=elapsed,
                state=AgentState.FAILED,
                metadata={"error": str(exc)},
            )
        finally:
            self.workload = max(0, self.workload - 1)

    @abstractmethod
    def think(self, task: Task) -> tuple[str, float]:
        """Process the task and return (output_text, confidence_0_to_1)."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        perf = session_store.get_agent_performance(self.agent_id)
        return {
            "agent_id": self.agent_id,
            "name": self.__class__.__name__,
            "department": self.department,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "tools": list(self.tools),
            "model_preference": self.model_preference,
            "state": self.state.value,
            "workload": self.workload,
            "confidence": perf.get("avg_confidence", 0.0),
            "performance": perf,
        }
