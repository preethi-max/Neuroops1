"""NeuroOps Advanced Agent Registry.

Centralized registry of every available AI agent. The CEO queries this
registry to discover and select agents based on:
  - required skills (capabilities)
  - availability (state + workload)
  - previous performance (success rate, avg confidence)
  - confidence score

Each registered agent exposes:
  agent_id, name, department, role, description, capabilities,
  available tools, model preference, confidence score, workload,
  current state, performance history.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any, Dict, List, Optional, Type

from core import AgentState, Department
from core.base_agent import BaseAgent
from core.event_bus import event_bus
from core.storage import session_store
from agents.engineering import (
    BackendAgent,
    DebuggingAgent,
    FrontendAgent,
    SoftwareEngineerAgent,
)
from agents.design import AccessibilityAgent, UIUXDesignerAgent
from agents.testing import QAAgent, SecurityTestingAgent
from agents.research import DocumentationAgent, ResearchAgent
from agents.support_agents import (
    KnowledgeManagerAgent,
    NotificationAgent,
    TaskPlannerAgent,
)


# Agent type -> class mapping
AGENT_TYPES: Dict[str, Type[BaseAgent]] = {
    "software_engineer": SoftwareEngineerAgent,
    "backend": BackendAgent,
    "frontend": FrontendAgent,
    "debugging": DebuggingAgent,
    "ui_ux_designer": UIUXDesignerAgent,
    "accessibility": AccessibilityAgent,
    "qa": QAAgent,
    "security_testing": SecurityTestingAgent,
    "research": ResearchAgent,
    "documentation": DocumentationAgent,
    "task_planner": TaskPlannerAgent,
    "notification": NotificationAgent,
    "knowledge_manager": KnowledgeManagerAgent,
}

# Skill -> agent types that provide that skill
SKILL_INDEX: Dict[str, List[str]] = {
    "architecture": ["software_engineer", "backend"],
    "implementation": ["software_engineer", "backend", "frontend"],
    "code_review": ["software_engineer"],
    "refactoring": ["software_engineer"],
    "api_design": ["backend"],
    "database_modeling": ["backend"],
    "authentication": ["backend"],
    "performance": ["backend"],
    "ui_implementation": ["frontend"],
    "responsive_design": ["frontend"],
    "state_management": ["frontend"],
    "ui_design": ["ui_ux_designer"],
    "ux_research": ["ui_ux_designer"],
    "wireframing": ["ui_ux_designer"],
    "prototyping": ["ui_ux_designer"],
    "design_systems": ["ui_ux_designer"],
    "wcag_audit": ["accessibility"],
    "aria_review": ["accessibility"],
    "contrast_analysis": ["accessibility"],
    "unit_testing": ["qa"],
    "integration_testing": ["qa"],
    "edge_case_analysis": ["qa"],
    "test_automation": ["qa"],
    "owasp_audit": ["security_testing"],
    "vulnerability_scan": ["security_testing"],
    "threat_modeling": ["security_testing"],
    "information_retrieval": ["research"],
    "literature_review": ["research"],
    "summarization": ["research"],
    "technical_writing": ["documentation"],
    "api_documentation": ["documentation"],
    "readme_generation": ["documentation"],
    "task_decomposition": ["task_planner"],
    "dependency_analysis": ["task_planner"],
    "notification_formatting": ["notification"],
    "stakeholder_communication": ["notification"],
    "memory_consolidation": ["knowledge_manager"],
    "knowledge_retrieval": ["knowledge_manager"],
    "context_preservation": ["knowledge_manager"],
    "debugging": ["debugging"],
    "root_cause_analysis": ["debugging"],
    "fix_proposal": ["debugging"],
}


class AgentRegistry:
    """Centralized registry for all NeuroOps agents.

    Maintains agent metadata, live state, workload, and performance history.
    The CEO queries this to form teams dynamically.
    """

    def __init__(self):
        self._lock = threading.RLock()
        # agent_type -> list of live instances (pool)
        self._pools: Dict[str, List[BaseAgent]] = {}
        # agent_type -> metadata (static spec)
        self._specs: Dict[str, Dict[str, Any]] = {}
        self._build_specs()

    def _build_specs(self):
        for agent_type, cls in AGENT_TYPES.items():
            self._specs[agent_type] = {
                "agent_type": agent_type,
                "name": cls.__name__,
                "department": cls.department,
                "role": agent_type.replace("_", " ").title(),
                "description": cls.description,
                "capabilities": list(cls.capabilities),
                "tools": list(cls.tools),
                "model_preference": cls.model_preference,
                "confidence": 0.0,
                "workload": 0,
                "current_state": AgentState.SLEEPING.value,
                "performance_history": [],
            }
            event_bus.emit(
                "agent:registered",
                source="AgentRegistry",
                message=f"Registered agent: {cls.__name__} ({cls.department})",
                data={"agent_type": agent_type, "name": cls.__name__, "department": cls.department},
            )

    # ---- Discovery ----
    def list_agents(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self.get_agent_spec(at) for at in AGENT_TYPES]

    def get_agent_spec(self, agent_type: str) -> Dict[str, Any]:
        spec = dict(self._specs.get(agent_type, {}))
        # Merge live performance data
        perf = {}
        with self._lock:
            instances = self._pools.get(agent_type, [])
            if instances:
                # Aggregate performance across instances
                total_completed = 0
                total_failed = 0
                total_conf = 0.0
                total_time = 0.0
                for inst in instances:
                    p = session_store.get_agent_performance(inst.agent_id)
                    total_completed += p.get("tasks_completed", 0)
                    total_failed += p.get("tasks_failed", 0)
                    total_conf += p.get("total_confidence", 0.0)
                    total_time += p.get("total_exec_time_ms", 0.0)
                n = total_completed + total_failed
                perf = {
                    "tasks_completed": total_completed,
                    "tasks_failed": total_failed,
                    "success_rate": total_completed / max(1, n),
                    "avg_confidence": total_conf / max(1, n),
                    "avg_exec_time_ms": total_time / max(1, n),
                    "workload": sum(i.workload for i in instances),
                    "current_state": instances[-1].state.value,
                }
        spec.update(perf)
        return spec

    def find_by_skill(self, skill: str) -> List[str]:
        """Return agent types that provide the given skill."""
        return list(SKILL_INDEX.get(skill, []))

    def find_by_skills(self, skills: List[str]) -> List[str]:
        """Return agent types matching ANY of the skills, ranked by match count."""
        scores: Dict[str, int] = {}
        for s in skills:
            for at in self.find_by_skill(s):
                scores[at] = scores.get(at, 0) + 1
        return [at for at, _ in sorted(scores.items(), key=lambda x: -x[1])]

    def select_best(self, skills: List[str], exclude: Optional[set] = None) -> Optional[str]:
        """Select the best agent type for the given skills.

        Scoring: skill match (60%) + performance success rate (25%) + low workload (15%).
        """
        candidates = self.find_by_skills(skills)
        if exclude:
            candidates = [c for c in candidates if c not in exclude]
        if not candidates:
            # Fallback: if no skill match, try all agents
            candidates = list(AGENT_TYPES.keys())

        best = None
        best_score = -1.0
        for at in candidates:
            spec = self.get_agent_spec(at)
            skill_score = 1.0 if at in self.find_by_skills(skills) else 0.0
            success = spec.get("success_rate", 0.5)
            workload = spec.get("workload", 0)
            workload_score = 1.0 / (1.0 + workload)
            score = 0.6 * skill_score + 0.25 * success + 0.15 * workload_score
            if score > best_score:
                best_score = score
                best = at
        return best

    # ---- Activation ----
    def acquire(self, agent_type: str) -> Optional[BaseAgent]:
        """Wake (instantiate) an agent of the given type, or reuse an available one."""
        with self._lock:
            pool = self._pools.setdefault(agent_type, [])
            # Reuse an available/sleeping instance
            for inst in pool:
                if inst.state in (AgentState.SLEEPING, AgentState.AVAILABLE):
                    inst.set_state(AgentState.AVAILABLE)
                    event_bus.emit(
                        "agent:activated",
                        source=inst.agent_id,
                        message=f"Agent activated: {inst.__class__.__name__} ({inst.department})",
                        agent_id=inst.agent_id,
                        data={"agent_type": agent_type, "department": inst.department},
                    )
                    return inst
            # Create a new instance
            cls = AGENT_TYPES.get(agent_type)
            if cls is None:
                return None
            instance = cls()
            pool.append(instance)
            session_store.set_agent_state(instance.agent_id, AgentState.AVAILABLE)
            event_bus.emit(
                "agent:activated",
                source=instance.agent_id,
                message=f"Agent activated: {cls.__name__} ({cls.department})",
                agent_id=instance.agent_id,
                data={"agent_type": agent_type, "department": cls.department},
            )
            return instance

    def release(self, agent: BaseAgent):
        """Return an agent to sleeping state after work is done."""
        agent.set_state(AgentState.SLEEPING)

    def sleep_unused(self, active_types: set):
        """Put agents not in active_types back to sleep."""
        with self._lock:
            for agent_type, pool in self._pools.items():
                if agent_type not in active_types:
                    for inst in pool:
                        if inst.state != AgentState.SLEEPING:
                            inst.set_state(AgentState.SLEEPING)

    def all_states(self) -> Dict[str, str]:
        """Return agent_type -> current state for all live agents."""
        with self._lock:
            states = {}
            for at, pool in self._pools.items():
                if pool:
                    states[at] = pool[-1].state.value
                else:
                    states[at] = AgentState.SLEEPING.value
            return states


# Singleton registry
agent_registry = AgentRegistry()
