"""NeuroOps core data models (Phase 2).

Pure Python dataclasses used by the in-memory workflow layer.
Designed so a real DB (SQLite/PostgreSQL) can replace the storage
backend without touching agent or workflow logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentState(str, Enum):
    SLEEPING = "sleeping"
    THINKING = "thinking"
    WORKING = "working"
    COMPLETED = "completed"
    WAITING_APPROVAL = "waiting_approval"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Department(str, Enum):
    ENGINEERING = "engineering"
    DESIGN = "design"
    RESEARCH = "research"
    MANAGEMENT = "management"
    COMMUNICATION = "communication"
    MEMORY = "memory"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A unit of work produced by the Task Planner."""
    task_id: str
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    department: Optional[Department] = None
    required_agent: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    confidence: float = 0.0
    result: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value if isinstance(self.priority, Priority) else self.priority,
            "department": self.department.value if isinstance(self.department, Department) else self.department,
            "required_agent": self.required_agent,
            "dependencies": list(self.dependencies),
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "confidence": self.confidence,
            "result": self.result,
            "logs": list(self.logs),
            "assigned_agent": self.assigned_agent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retries": self.retries,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Agent result
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Structured output returned by every agent."""
    agent_id: str
    task_id: str
    output: str
    confidence: float
    logs: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    state: AgentState = AgentState.COMPLETED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "output": self.output,
            "confidence": self.confidence,
            "logs": list(self.logs),
            "execution_time_ms": self.execution_time_ms,
            "state": self.state.value if isinstance(self.state, AgentState) else self.state,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Timeline event
# ---------------------------------------------------------------------------

@dataclass
class TimelineEvent:
    """A single event in the execution timeline."""
    event_id: str
    timestamp: datetime
    event_type: str
    source: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "source": self.source,
            "message": self.message,
            "data": dict(self.data),
        }


# ---------------------------------------------------------------------------
# Conversation message
# ---------------------------------------------------------------------------

@dataclass
class ConversationMessage:
    role: str  # "user" | "ceo" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": dict(self.metadata),
        }
