"""NeuroOps Human-in-the-Loop approval system.

When an agent's confidence is below a threshold or a high-risk action is
detected, the system enters WAITING_FOR_HUMAN_APPROVAL. The user can:
  - Approve
  - Reject
  - Request modification
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from core import ApprovalRequest, AgentState, Task, TaskStatus
from core.event_bus import event_bus
from core.storage import session_store


class ApprovalService:
    """Manages human approval requests and responses."""

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

    def needs_approval(self, confidence: float, task: Task) -> bool:
        """Determine if a task result requires human approval."""
        if confidence < self.confidence_threshold:
            return True
        # High-risk keywords
        high_risk = any(kw in task.title.lower() for kw in ["delete", "drop", "deploy", "production", "migration"])
        if high_risk:
            return True
        return False

    def request_approval(self, task: Task, agent_id: str, confidence: float, reason: str) -> ApprovalRequest:
        """Create an approval request and put the task in waiting state."""
        req = ApprovalRequest(
            approval_id=f"appr-{uuid.uuid4().hex[:8]}",
            task_id=task.task_id,
            agent_id=agent_id,
            reason=reason,
            confidence=confidence,
        )
        session_store.add_approval(req)
        task.status = TaskStatus.WAITING_APPROVAL
        task.needs_approval = True
        session_store.update_task(task.task_id, status=TaskStatus.WAITING_APPROVAL, needs_approval=True)
        event_bus.emit(
            "human:approval_required",
            source="ApprovalService",
            message=f"Approval required for task {task.task_id}: {reason}",
            agent_id=agent_id,
            data=req.to_dict(),
        )
        return req

    def resolve(self, approval_id: str, decision: str, notes: Optional[str] = None) -> Optional[ApprovalRequest]:
        """Resolve an approval: approved | rejected | modification."""
        req = session_store.update_approval(approval_id, decision, notes)
        if not req:
            return None
        task = session_store.get_task(req.task_id)
        if task:
            task.approval_status = decision
            session_store.update_task(task.task_id, approval_status=decision)
            if decision == "approved":
                task.status = TaskStatus.COMPLETED
                session_store.update_task(task.task_id, status=TaskStatus.COMPLETED)
            elif decision == "rejected":
                task.status = TaskStatus.FAILED
                session_store.update_task(task.task_id, status=TaskStatus.FAILED)
            elif decision == "modification":
                task.status = TaskStatus.PENDING
                session_store.update_task(task.task_id, status=TaskStatus.PENDING)
        event_bus.emit(
            f"human:approval_{decision}",
            source="ApprovalService",
            message=f"Approval {decision} for task {req.task_id}",
            agent_id=req.agent_id,
            data=req.to_dict(),
        )
        return req

    def get_pending(self):
        return session_store.get_pending_approvals()


# Singleton
approval_service = ApprovalService()
