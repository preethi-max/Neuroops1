"""NeuroOps in-memory storage layer.

Isolated behind service classes so SQLite/PostgreSQL can replace it
later without touching agent or workflow logic. All state lives here.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import (
    AgentState,
    ConversationMessage,
    Task,
    TaskStatus,
    TimelineEvent,
)


class SessionStore:
    """Thread-safe in-memory store for one NeuroOps session.

    Holds: tasks, task graph, agent states, timeline events,
    conversation history, memory summaries, and session metadata.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._reset_locked()

    # -- internal init (must hold lock) --
    def _reset_locked(self):
        self.session_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.utcnow()
        self.tasks: Dict[str, Task] = {}
        self.task_graph: Dict[str, List[str]] = {}  # task_id -> dependent task_ids
        self.agent_states: Dict[str, AgentState] = {}
        self.agent_logs: Dict[str, List[str]] = {}
        self.timeline: List[TimelineEvent] = []
        self.conversation: List[ConversationMessage] = []
        self.memory_summaries: List[Dict[str, Any]] = []
        self.final_response: Optional[str] = None
        self.workflow_status: str = "idle"  # idle|running|completed|failed

    # -- public API --
    def reset(self):
        with self._lock:
            self._reset_locked()

    def get_session(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id": self.session_id,
                "created_at": self.created_at.isoformat(),
                "workflow_status": self.workflow_status,
                "task_count": len(self.tasks),
                "agent_count": len(self.agent_states),
                "event_count": len(self.timeline),
                "final_response": self.final_response,
            }

    # ---- Tasks ----
    def add_task(self, task: Task):
        with self._lock:
            self.tasks[task.task_id] = task
            self.task_graph.setdefault(task.task_id, [])
            for dep in task.dependencies:
                self.task_graph.setdefault(dep, []).append(task.task_id)

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        with self._lock:
            return list(self.tasks.values())

    def update_task(self, task_id: str, **fields):
        with self._lock:
            t = self.tasks.get(task_id)
            if not t:
                return None
            for k, v in fields.items():
                if hasattr(t, k):
                    setattr(t, k, v)
            return t

    def get_task_graph(self) -> Dict[str, List[str]]:
        with self._lock:
            return {k: list(v) for k, v in self.task_graph.items()}

    # ---- Agent states ----
    def set_agent_state(self, agent_id: str, state: AgentState):
        with self._lock:
            self.agent_states[agent_id] = state

    def get_agent_state(self, agent_id: str) -> AgentState:
        with self._lock:
            return self.agent_states.get(agent_id, AgentState.SLEEPING)

    def get_all_agent_states(self) -> Dict[str, str]:
        with self._lock:
            return {aid: s.value for aid, s in self.agent_states.items()}

    def add_agent_log(self, agent_id: str, line: str):
        with self._lock:
            self.agent_logs.setdefault(agent_id, []).append(line)

    def get_agent_logs(self, agent_id: str) -> List[str]:
        with self._lock:
            return list(self.agent_logs.get(agent_id, []))

    # ---- Timeline ----
    def add_event(self, event: TimelineEvent):
        with self._lock:
            self.timeline.append(event)

    def get_timeline(self) -> List[TimelineEvent]:
        with self._lock:
            return list(self.timeline)

    # ---- Conversation ----
    def add_message(self, msg: ConversationMessage):
        with self._lock:
            self.conversation.append(msg)

    def get_conversation(self) -> List[ConversationMessage]:
        with self._lock:
            return list(self.conversation)

    # ---- Memory summaries ----
    def add_memory_summary(self, summary: Dict[str, Any]):
        with self._lock:
            self.memory_summaries.append(summary)

    def get_memory_summaries(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.memory_summaries)

    # ---- Workflow status ----
    def set_workflow_status(self, status: str):
        with self._lock:
            self.workflow_status = status

    def set_final_response(self, response: str):
        with self._lock:
            self.final_response = response


# Singleton store for the current session.
session_store = SessionStore()
