"""NeuroOps Task Planner.

Converts the CEO's reasoning into structured subtasks with a DAG:
  - Task ID
  - Title
  - Description
  - Priority
  - Required Department
  - Required Agent
  - Dependencies
  - Status
  - Confidence
"""
from __future__ import annotations

import re
import uuid
from typing import List

from core import Department, Priority, Task, TaskStatus
from core.event_bus import event_bus
from core.storage import session_store


# Keyword -> (agent_type, department) mapping for intent detection.
_KEYWORD_MAP = [
    (r"\b(code|implement|function|class|api|endpoint|build|develop)\b", "code_writer", Department.ENGINEERING),
    (r"\b(debug|fix|bug|error|crash|traceback)\b", "debugger", Department.ENGINEERING),
    (r"\b(review|quality|check|audit|inspect)\b", "reviewer", Department.ENGINEERING),
    (r"\b(document|docs|readme|guide|manual)\b", "documentation", Department.ENGINEERING),
    (r"\b(ui|interface|ux|design|layout|component|button|form)\b", "ui_suggestion", Department.DESIGN),
    (r"\b(wireframe|mockup|prototype|sketch)\b", "wireframe", Department.DESIGN),
    (r"\b(search|find|lookup|document|research|investigate)\b", "document_search", Department.RESEARCH),
    (r"\b(summar|condense|tldr|brief|abstract)\b", "summarizer", Department.RESEARCH),
    (r"\b(notif|alert|email|message|inform|announce)\b", "notification", Department.COMMUNICATION),
    (r"\b(remember|memory|store|recall|persist)\b", "memory", Department.MEMORY),
    (r"\b(plan|schedule|decompose|break.?down|organize)\b", "task_planner", Department.MANAGEMENT),
]


def _detect_intents(text: str) -> list[tuple[str, Department]]:
    text_lower = text.lower()
    matches = []
    seen = set()
    for pattern, agent_type, dept in _KEYWORD_MAP:
        if re.search(pattern, text_lower) and agent_type not in seen:
            matches.append((agent_type, dept))
            seen.add(agent_type)
    return matches


class TaskPlanner:
    """Converts a user request into a structured task DAG."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def plan(self, request: str) -> List[Task]:
        """Analyze request and produce a list of Tasks with dependencies."""
        event_bus.emit("planner:started", source="TaskPlanner", message="Analyzing request and building task DAG")

        intents = _detect_intents(request)
        if not intents:
            # Default plan: research -> implement -> review -> document -> notify
            intents = [
                ("document_search", Department.RESEARCH),
                ("code_writer", Department.ENGINEERING),
                ("reviewer", Department.ENGINEERING),
                ("documentation", Department.ENGINEERING),
                ("notification", Department.COMMUNICATION),
            ]

        tasks: List[Task] = []
        prev_id = None
        for idx, (agent_type, dept) in enumerate(intents):
            task_id = f"task-{idx+1}"
            deps = [prev_id] if prev_id else []
            title = f"{agent_type.replace('_', ' ').title()} for: {request[:60]}"
            task = Task(
                task_id=task_id,
                title=title,
                description=f"Execute {agent_type} analysis for request: {request}",
                priority=Priority.HIGH if idx < 2 else Priority.MEDIUM,
                department=dept,
                required_agent=agent_type,
                dependencies=deps,
                status=TaskStatus.READY if not deps else TaskStatus.PENDING,
                confidence=0.8,
            )
            tasks.append(task)
            session_store.add_task(task)
            event_bus.emit(
                "task:created",
                source="TaskPlanner",
                message=f"Created task {task_id}: {agent_type}",
                data=task.to_dict(),
            )
            prev_id = task_id

        # Always add a memory task at the end (no dependency on chain — runs after all)
        mem_id = f"task-{len(intents)+1}"
        mem_deps = [t.task_id for t in tasks]
        mem_task = Task(
            task_id=mem_id,
            title=f"Memory consolidation for: {request[:60]}",
            description="Store session summary in memory.",
            priority=Priority.LOW,
            department=Department.MEMORY,
            required_agent="memory",
            dependencies=mem_deps,
            status=TaskStatus.PENDING,
            confidence=0.9,
        )
        tasks.append(mem_task)
        session_store.add_task(mem_task)
        event_bus.emit(
            "task:created",
            source="TaskPlanner",
            message=f"Created task {mem_id}: memory",
            data=mem_task.to_dict(),
        )

        event_bus.emit(
            "planner:completed",
            source="TaskPlanner",
            message=f"Built DAG with {len(tasks)} tasks",
            data={"task_count": len(tasks)},
        )
        return tasks
