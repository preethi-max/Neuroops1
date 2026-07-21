"""NeuroOps Task Planner.

Converts the CEO's reasoning into structured subtasks with a DAG.
Each task includes:
  Task ID, Title, Description, Priority, Required Department,
  Required Agent, Required Skills, Dependencies, Status, Confidence.
"""
from __future__ import annotations

import re
import uuid
from typing import List

from core import Department, Priority, Task, TaskStatus
from core.event_bus import event_bus
from core.storage import session_store


# Keyword -> (skills, department) mapping for intent detection.
_KEYWORD_MAP = [
    (r"\b(code|implement|function|class|api|endpoint|build|develop|feature)\b",
     ["architecture", "implementation"], Department.ENGINEERING),
    (r"\b(backend|server|database|sql|model|schema|auth)\b",
     ["api_design", "database_modeling"], Department.ENGINEERING),
    (r"\b(frontend|client|component|page|render|dom)\b",
     ["ui_implementation", "responsive_design"], Department.ENGINEERING),
    (r"\b(debug|fix|bug|error|crash|traceback|exception)\b",
     ["root_cause_analysis", "fix_proposal"], Department.ENGINEERING),
    (r"\b(ui|ux|interface|design|layout|wireframe|prototype)\b",
     ["ui_design", "wireframing"], Department.DESIGN),
    (r"\b(accessib|wcag|aria|contrast|screen.?reader)\b",
     ["wcag_audit", "aria_review"], Department.DESIGN),
    (r"\b(test|qa|unit.?test|integration.?test|edge.?case)\b",
     ["unit_testing", "integration_testing"], Department.TESTING),
    (r"\b(security|vulnerab|owasp|inject|xss|penetration)\b",
     ["owasp_audit", "vulnerability_scan"], Department.TESTING),
    (r"\b(research|investigate|find|explore|analyze)\b",
     ["information_retrieval", "summarization"], Department.RESEARCH),
    (r"\b(document|readme|guide|manual|docs)\b",
     ["technical_writing", "readme_generation"], Department.RESEARCH),
    (r"\b(notif|alert|email|message|inform|announce)\b",
     ["notification_formatting", "stakeholder_communication"], Department.COMMUNICATION),
    (r"\b(remember|memory|store|recall|persist|checkpoint)\b",
     ["memory_consolidation", "knowledge_retrieval"], Department.MEMORY),
    (r"\b(plan|schedule|decompose|break.?down|organize)\b",
     ["task_decomposition", "dependency_analysis"], Department.MANAGEMENT),
]


def _detect_skills(text: str) -> list[tuple[list[str], Department]]:
    text_lower = text.lower()
    matches = []
    seen_skills = set()
    for pattern, skills, dept in _KEYWORD_MAP:
        if re.search(pattern, text_lower):
            new_skills = [s for s in skills if s not in seen_skills]
            if new_skills:
                matches.append((skills, dept))
                seen_skills.update(skills)
    return matches


class TaskPlanner:
    """Converts a user request into a structured task DAG."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    def plan(self, request: str, analysis: dict | None = None) -> List[Task]:
        """Analyze request and produce a list of Tasks with dependencies."""
        event_bus.emit("planner:started", source="TaskPlanner", message="Analyzing request and building task DAG")

        skill_matches = _detect_skills(request)
        if not skill_matches:
            # Default plan: research -> implement -> test -> document -> memory
            skill_matches = [
                (["information_retrieval"], Department.RESEARCH),
                (["architecture", "implementation"], Department.ENGINEERING),
                (["unit_testing", "integration_testing"], Department.TESTING),
                (["technical_writing"], Department.RESEARCH),
            ]

        tasks: List[Task] = []
        prev_id = None
        for idx, (skills, dept) in enumerate(skill_matches):
            task_id = f"task-{idx+1}"
            deps = [prev_id] if prev_id else []
            title = f"{dept.value.title()}: {request[:50]}"
            task = Task(
                task_id=task_id,
                title=title,
                description=f"Execute {', '.join(skills)} for: {request}",
                priority=Priority.HIGH if idx < 2 else Priority.MEDIUM,
                department=dept,
                required_skills=skills,
                dependencies=deps,
                status=TaskStatus.READY if not deps else TaskStatus.PENDING,
                confidence=0.8,
            )
            tasks.append(task)
            session_store.add_task(task)
            event_bus.emit(
                "task:created",
                source="TaskPlanner",
                message=f"Created task {task_id}: {skills[0]}",
                data=task.to_dict(),
            )
            prev_id = task_id

        # Always add a memory consolidation task at the end
        mem_id = f"task-{len(tasks)+1}"
        mem_deps = [t.task_id for t in tasks]
        mem_task = Task(
            task_id=mem_id,
            title=f"Memory consolidation for: {request[:50]}",
            description="Store session summary and project checkpoint.",
            priority=Priority.LOW,
            department=Department.MEMORY,
            required_skills=["memory_consolidation", "knowledge_retrieval"],
            dependencies=mem_deps,
            status=TaskStatus.PENDING,
            confidence=0.9,
        )
        tasks.append(mem_task)
        session_store.add_task(mem_task)
        event_bus.emit(
            "task:created",
            source="TaskPlanner",
            message=f"Created task {mem_id}: memory consolidation",
            data=mem_task.to_dict(),
        )

        event_bus.emit(
            "planner:completed",
            source="TaskPlanner",
            message=f"Built DAG with {len(tasks)} tasks",
            data={"task_count": len(tasks)},
        )
        return tasks
