"""NeuroOps Management, Communication, and Memory Department agents."""
from __future__ import annotations

from datetime import datetime

from core import Task
from core.base_agent import BaseAgent
from core.storage import session_store


class TaskPlannerAgent(BaseAgent):
    department = "management"
    description = "Converts CEO reasoning into structured subtasks with dependencies."
    capabilities = ["task_decomposition", "dependency_analysis", "priority_assignment", "dag_construction"]
    tools = ["task_graph", "priority_matrix"]
    model_preference = "openai"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Decomposing request into subtasks...")
        resp = self.call_model(
            "You are a task planner. Break the request into ordered subtasks with dependencies.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Task plan generated.")
        return resp.content, resp.confidence


class NotificationAgent(BaseAgent):
    department = "communication"
    description = "Formats and dispatches notifications to stakeholders."
    capabilities = ["notification_formatting", "stakeholder_communication", "status_reporting"]
    tools = ["email_client", "slack_webhook", "template_engine"]
    model_preference = "stub"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Composing notification...")
        resp = self.call_model(
            "You are a notification agent. Compose a clear status update.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Notification ready.")
        return resp.content, resp.confidence


class KnowledgeManagerAgent(BaseAgent):
    department = "memory"
    description = "Manages episodic, semantic, project, and agent memory."
    capabilities = ["memory_consolidation", "knowledge_retrieval", "context_preservation", "checkpointing"]
    tools = ["memory_store", "vector_index", "checkpoint_manager"]
    model_preference = "stub"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Consolidating memory...")
        resp = self.call_model(
            "You are a knowledge manager. Summarize what was learned and store it for future retrieval.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        # Store a project memory entry
        from core import MemoryEntry, MemoryType
        session_store.add_memory(MemoryEntry(
            memory_id=f"mem-{datetime.utcnow().strftime('%H%M%S%f')}",
            memory_type=MemoryType.PROJECT,
            content=f"Completed: {task.title}",
            agent_id=self.agent_id,
            metadata={"task_id": task.task_id},
        ))
        self.log("Memory consolidated and stored.")
        return resp.content, resp.confidence
