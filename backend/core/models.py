"""NeuroOps core data models.

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
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    ASSIGNED = "assigned"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
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
    TESTING = "testing"
    RESEARCH = "research"
    MANAGEMENT = "management"
    COMMUNICATION = "communication"
    MEMORY = "memory"


class MemoryType(str, Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROJECT = "project"
    AGENT = "agent"


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
    required_skills: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    confidence: float = 0.0
    result: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    needs_approval: bool = False
    approval_status: Optional[str] = None  # "approved" | "rejected" | None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value if isinstance(self.priority, Priority) else self.priority,
            "department": self.department.value if isinstance(self.department, Department) else self.department,
            "required_agent": self.required_agent,
            "required_skills": list(self.required_skills),
            "dependencies": list(self.dependencies),
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "confidence": self.confidence,
            "result": self.result,
            "logs": list(self.logs),
            "assigned_agent": self.assigned_agent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retries": self.retries,
            "needs_approval": self.needs_approval,
            "approval_status": self.approval_status,
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
    trace_id: str
    event_type: str
    source: str
    agent_id: Optional[str]
    previous_state: Optional[str]
    new_state: Optional[str]
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "event_type": self.event_type,
            "source": self.source,
            "agent_id": self.agent_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
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


# ---------------------------------------------------------------------------
# Memory entry
# ---------------------------------------------------------------------------

@dataclass
class MemoryEntry:
    memory_id: str
    memory_type: MemoryType
    content: str
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Approval request
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    approval_id: str
    task_id: str
    agent_id: str
    reason: str
    confidence: float
    status: str = "pending"  # "pending" | "approved" | "rejected" | "modification"
    modification_notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "reason": self.reason,
            "confidence": self.confidence,
            "status": self.status,
            "modification_notes": self.modification_notes,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
