"""NeuroOps Management, Communication, and Memory Department agents."""
from __future__ import annotations

from datetime import datetime

from core import Task
from core.base_agent import BaseAgent
from core.storage import session_store


class TaskPlannerAgent(BaseAgent):
    department = "management"
    description = "Converts CEO reasoning into structured subtasks."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Decomposing request into subtasks...")
        plan = [
            "## Task Plan",
            "",
            f"Source request: {task.title}",
            "",
            "Proposed subtasks:",
            "1. Research relevant documentation (research / document_search)",
            "2. Write implementation (engineering / code_writer)",
            "3. Review implementation (engineering / reviewer)",
            "4. Generate documentation (engineering / documentation)",
            "5. Notify stakeholders (communication / notification)",
            "",
            "Dependencies: 2 depends on 1; 3 depends on 2; 4 depends on 2; 5 depends on 3,4",
        ]
        self.log("Plan generated with 5 subtasks.")
        return "\n".join(plan), 0.83


class NotificationAgent(BaseAgent):
    department = "communication"
    description = "Formats and dispatches notifications to stakeholders."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Composing notification...")
        notification = [
            "## Notification",
            "",
            f"Subject: {task.title} — Status Update",
            "",
            f"Body: Task '{task.title}' has been processed.",
            "All required agents have completed their work.",
            "Please review the final output.",
            "",
            f"Timestamp: {datetime.utcnow().isoformat()}",
        ]
        self.log("Notification ready for dispatch.")
        return "\n".join(notification), 0.9


class MemoryAgent(BaseAgent):
    department = "memory"
    description = "Stores and retrieves session memory summaries."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Consolidating memory...")
        summary = {
            "task_id": task.task_id,
            "title": task.title,
            "summary": f"Processed: {task.title}",
            "timestamp": datetime.utcnow().isoformat(),
        }
        session_store.add_memory_summary(summary)
        self.log("Memory summary stored.")
        report = (
            "## Memory Stored\n\n"
            f"- Task: {task.title}\n"
            "- Summary recorded for future retrieval.\n"
            "- Ready for long-term memory integration (Phase 3+)."
        )
        return report, 0.87
