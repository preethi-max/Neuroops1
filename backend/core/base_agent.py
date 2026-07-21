"""NeuroOps base agent contract.

Every agent follows the same contract:
  - receive structured task input
  - think
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


class BaseAgent(ABC):
    """Abstract base for all NeuroOps agents."""

    department: str = "general"
    description: str = ""

    def __init__(self, agent_id: Optional[str] = None):
        self.agent_id = agent_id or f"{self.__class__.__name__}-{uuid.uuid4().hex[:6]}"
        self.state: AgentState = AgentState.SLEEPING
        self.logs: List[str] = []

    # ---- State management (emits events) ----
    def set_state(self, new_state: AgentState, task_id: Optional[str] = None):
        old = self.state
        self.state = new_state
        session_store.set_agent_state(self.agent_id, new_state)
        self._emit_state_event(new_state, old, task_id)

    def _emit_state_event(self, new_state: AgentState, old_state: AgentState, task_id: Optional[str]):
        event_map = {
            AgentState.THINKING: ("agent:thinking", "Thinking"),
            AgentState.WORKING: ("agent:working", "Working"),
            AgentState.COMPLETED: ("agent:completed", "Completed"),
            AgentState.FAILED: ("agent:failed", "Failed"),
            AgentState.WAITING_APPROVAL: ("agent:waiting_approval", "Waiting Approval"),
            AgentState.SLEEPING: ("agent:sleeping", "Sleeping"),
        }
        event_type, label = event_map.get(new_state, ("agent:state", new_state.value))
        event_bus.emit(
            event_type,
            source=self.agent_id,
            message=f"{self.__class__.__name__} -> {label}",
            data={
                "agent_id": self.agent_id,
                "agent_name": self.__class__.__name__,
                "department": self.department,
                "old_state": old_state.value,
                "new_state": new_state.value,
                "task_id": task_id,
            },
        )

    def log(self, message: str):
        line = f"[{datetime.utcnow().isoformat()}] {message}"
        self.logs.append(line)
        session_store.add_agent_log(self.agent_id, line)

    # ---- Public execution contract ----
    def execute(self, task: Task) -> AgentResult:
        """Run the full agent lifecycle. Subclasses implement `think`."""
        self.logs = []
        start = time.time()
        self.set_state(AgentState.THINKING, task.task_id)
        self.log(f"Task assigned: {task.title}")
        event_bus.emit(
            "agent:task_assigned",
            source=self.agent_id,
            message=f"Task assigned to {self.__class__.__name__}: {task.title}",
            data={"agent_id": self.agent_id, "task_id": task.task_id, "title": task.title},
        )
        try:
            self.set_state(AgentState.WORKING, task.task_id)
            output, confidence = self.think(task)
            elapsed = (time.time() - start) * 1000
            self.set_state(AgentState.COMPLETED, task.task_id)
            self.log(f"Completed in {elapsed:.1f}ms (confidence={confidence:.2f})")
            event_bus.emit(
                "agent:task_finished",
                source=self.agent_id,
                message=f"{self.__class__.__name__} finished task {task.task_id}",
                data={
                    "agent_id": self.agent_id,
                    "task_id": task.task_id,
                    "confidence": confidence,
                    "execution_time_ms": elapsed,
                },
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
            event_bus.emit(
                "agent:failed",
                source=self.agent_id,
                message=f"{self.__class__.__name__} failed on task {task.task_id}: {exc}",
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

    @abstractmethod
    def think(self, task: Task) -> tuple[str, float]:
        """Process the task and return (output_text, confidence_0_to_1)."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.__class__.__name__,
            "department": self.department,
            "description": self.description,
            "state": self.state.value,
        }
