"""NeuroOps in-memory storage layer.

Isolated behind service classes so SQLite/PostgreSQL can replace it
later without touching agent or workflow logic. All session state lives here.
"""
from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import (
    AgentState,
    ApprovalRequest,
    ConversationMessage,
    MemoryEntry,
    Task,
    TimelineEvent,
)


class SessionStore:
    """Thread-safe in-memory store for one NeuroOps session.

    Holds: tasks, task graph, agent states, agent performance,
    timeline events, conversation history, memory entries,
    approval requests, and session metadata.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._reset_locked()

    def _reset_locked(self):
        self.session_id: str = str(uuid.uuid4())
        self.trace_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.utcnow()
        self.tasks: Dict[str, Task] = {}
        self.task_graph: Dict[str, List[str]] = {}
        self.agent_states: Dict[str, AgentState] = {}
        self.agent_logs: Dict[str, List[str]] = {}
        self.agent_performance: Dict[str, Dict[str, Any]] = {}
        self.timeline: List[TimelineEvent] = []
        self.conversation: List[ConversationMessage] = []
        self.memory: List[MemoryEntry] = []
        self.approvals: Dict[str, ApprovalRequest] = {}
        self.final_response: Optional[str] = None
        self.workflow_status: str = "idle"

    def reset(self):
        with self._lock:
            self._reset_locked()

    def get_session(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id": self.session_id,
                "trace_id": self.trace_id,
                "created_at": self.created_at.isoformat(),
                "workflow_status": self.workflow_status,
                "task_count": len(self.tasks),
                "agent_count": len(self.agent_states),
                "event_count": len(self.timeline),
                "memory_count": len(self.memory),
                "approval_count": len(self.approvals),
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

    def update_task(self, task_id: str, **fields) -> Optional[Task]:
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

    # ---- Agent performance ----
    def record_agent_performance(self, agent_id: str, success: bool, confidence: float, exec_time_ms: float):
        with self._lock:
            perf = self.agent_performance.setdefault(agent_id, {
                "tasks_completed": 0, "tasks_failed": 0, "total_confidence": 0.0,
                "total_exec_time_ms": 0.0, "history": [],
            })
            if success:
                perf["tasks_completed"] += 1
            else:
                perf["tasks_failed"] += 1
            perf["total_confidence"] += confidence
            perf["total_exec_time_ms"] += exec_time_ms
            perf["history"].append({
                "success": success, "confidence": confidence,
                "exec_time_ms": exec_time_ms, "timestamp": datetime.utcnow().isoformat(),
            })
            perf["success_rate"] = perf["tasks_completed"] / max(1, perf["tasks_completed"] + perf["tasks_failed"])
            perf["avg_confidence"] = perf["total_confidence"] / max(1, perf["tasks_completed"] + perf["tasks_failed"])
            perf["avg_exec_time_ms"] = perf["total_exec_time_ms"] / max(1, perf["tasks_completed"] + perf["tasks_failed"])

    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        with self._lock:
            return dict(self.agent_performance.get(agent_id, {}))

    def get_all_performance(self) -> Dict[str, Any]:
        with self._lock:
            return {aid: dict(p) for aid, p in self.agent_performance.items()}

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

    # ---- Memory ----
    def add_memory(self, entry: MemoryEntry):
        with self._lock:
            self.memory.append(entry)

    def get_memory(self, memory_type: Optional[str] = None, agent_id: Optional[str] = None) -> List[MemoryEntry]:
        with self._lock:
            results = list(self.memory)
            if memory_type:
                results = [m for m in results if m.memory_type.value == memory_type]
            if agent_id:
                results = [m for m in results if m.agent_id == agent_id]
            return results

    # ---- Approvals ----
    def add_approval(self, req: ApprovalRequest):
        with self._lock:
            self.approvals[req.approval_id] = req

    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self.approvals.get(approval_id)

    def get_pending_approvals(self) -> List[ApprovalRequest]:
        with self._lock:
            return [a for a in self.approvals.values() if a.status == "pending"]

    def update_approval(self, approval_id: str, status: str, notes: Optional[str] = None) -> Optional[ApprovalRequest]:
        with self._lock:
            a = self.approvals.get(approval_id)
            if not a:
                return None
            a.status = status
            a.modification_notes = notes
            a.resolved_at = datetime.utcnow()
            return a

    # ---- Workflow ----
    def set_workflow_status(self, status: str):
        with self._lock:
            self.workflow_status = status

    def set_final_response(self, response: str):
        with self._lock:
            self.final_response = response


# Singleton store for the current session.
session_store = SessionStore()
