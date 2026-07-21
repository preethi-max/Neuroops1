"""NeuroOps agent registry.

Maps agent type names to agent classes and provides lookup by
department. Used by the Scheduler to wake only the required agents.
"""
from __future__ import annotations

from typing import Dict, List, Type

from core.base_agent import BaseAgent
from agents.engineering import (
    CodeWriterAgent,
    DebuggerAgent,
    DocumentationAgent,
    ReviewerAgent,
)
from agents.design import UISuggestionAgent, WireframeAgent
from agents.research import DocumentSearchAgent, SummarizerAgent
from agents.support_agents import (
    MemoryAgent,
    NotificationAgent,
    TaskPlannerAgent,
)

# Canonical registry: agent_type -> class
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    # Engineering
    "code_writer": CodeWriterAgent,
    "debugger": DebuggerAgent,
    "reviewer": ReviewerAgent,
    "documentation": DocumentationAgent,
    # Design
    "ui_suggestion": UISuggestionAgent,
    "wireframe": WireframeAgent,
    # Research
    "document_search": DocumentSearchAgent,
    "summarizer": SummarizerAgent,
    # Management
    "task_planner": TaskPlannerAgent,
    # Communication
    "notification": NotificationAgent,
    # Memory
    "memory": MemoryAgent,
}


def get_agent_class(agent_type: str) -> Type[BaseAgent] | None:
    return AGENT_REGISTRY.get(agent_type)


def list_agent_types() -> List[str]:
    return list(AGENT_REGISTRY.keys())


def all_agent_metadata() -> List[dict]:
    return [
        {"agent_type": key, "name": cls.__name__, "department": cls.department, "description": cls.description}
        for key, cls in AGENT_REGISTRY.items()
    ]
