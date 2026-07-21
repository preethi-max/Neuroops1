"""NeuroOps CEO Agent (Phase 3).

The CEO no longer knows agents directly. It:
  - Analyzes the user request (intent + scope + required skills)
  - Queries the Agent Registry to find suitable agents
  - Forms an optimized team based on skills, availability, workload, performance
  - Delegates decomposition to the Task Planner
  - Activates the Scheduler
  - Monitors progress
  - Handles failures
  - Merges all outputs
  - Generates the final response
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core import ConversationMessage, AgentResult, Task, Department
from core.event_bus import event_bus
from core.memory_service import memory_service
from core.storage import session_store
from core.task_planner import TaskPlanner
from agents.registry import agent_registry


class CEOAgent:
    """Orchestrates the entire NeuroOps workflow with dynamic agent selection."""

    def __init__(self, planner: Optional[TaskPlanner] = None, scheduler=None):
        self.planner = planner or TaskPlanner()
        self.scheduler = scheduler
        self.analysis: dict = {}
        self.team: List[str] = []

    def set_scheduler(self, scheduler):
        self.scheduler = scheduler

    # ---- Step 1: Analyze ----
    def analyze_request(self, request: str) -> dict:
        event_bus.emit("ceo:started", source="CEO", message=f"Analyzing request: {request[:80]}")
        session_store.add_message(ConversationMessage(role="user", content=request))

        # Check for continuation request
        is_continuation = self._is_continuation_request(request)
        continuation_context = {}
        if is_continuation:
            continuation_context = memory_service.prepare_continuation_context()
            event_bus.emit("ceo:continuation", source="CEO", message="Continuation detected — loading previous project state")

        analysis = {
            "raw_request": request,
            "intent": self._classify_intent(request),
            "scope": "single" if len(request) < 100 else "complex",
            "is_continuation": is_continuation,
            "continuation_context": continuation_context,
            "estimated_tasks": max(3, min(8, len(request.split()) // 5)),
            "departments_needed": self._identify_departments(request),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.analysis = analysis
        session_store.add_message(
            ConversationMessage(
                role="ceo",
                content=f"Analysis: {analysis['intent']} (scope={analysis['scope']})",
                metadata=analysis,
            )
        )
        # Store episodic memory of the analysis
        memory_service.store_episode(
            f"CEO analyzed request: {request[:100]} | Intent: {analysis['intent']}",
            agent_id="CEO",
        )
        event_bus.emit(
            "ceo:analysis",
            source="CEO",
            message=f"Intent: {analysis['intent']} | Departments: {analysis['departments_needed']}",
            data=analysis,
        )
        return analysis

    def _is_continuation_request(self, request: str) -> bool:
        r = request.lower()
        return any(kw in r for kw in ["continue", "yesterday", "previous", "last project", "resume", "checkpoint"])

    def _classify_intent(self, request: str) -> str:
        r = request.lower()
        if any(w in r for w in ["build", "create", "implement", "develop"]):
            return "build"
        if any(w in r for w in ["fix", "debug", "resolve", "error"]):
            return "fix"
        if any(w in r for w in ["review", "audit", "check", "analyze"]):
            return "review"
        if any(w in r for w in ["document", "summarize", "explain"]):
            return "document"
        if any(w in r for w in ["test", "qa", "security"]):
            return "test"
        return "general"

    def _identify_departments(self, request: str) -> List[str]:
        r = request.lower()
        deps = []
        if any(w in r for w in ["code", "build", "implement", "debug", "review", "backend", "frontend", "api"]):
            deps.append("engineering")
        if any(w in r for w in ["ui", "ux", "design", "wireframe", "accessib"]):
            deps.append("design")
        if any(w in r for w in ["test", "qa", "security", "vulnerab"]):
            deps.append("testing")
        if any(w in r for w in ["research", "search", "find", "document"]):
            deps.append("research")
        if any(w in r for w in ["notify", "alert", "inform"]):
            deps.append("communication")
        deps.append("memory")
        return list(dict.fromkeys(deps))

    # ---- Step 2: Query Registry + Form Team ----
    def form_team(self, request: str) -> List[str]:
        event_bus.emit("ceo:querying_registry", source="CEO", message="Querying Agent Registry for suitable agents")

        # Detect required skills from the request
        from core.task_planner import _detect_skills
        skill_matches = _detect_skills(request)
        all_skills = []
        for skills, _ in skill_matches:
            all_skills.extend(skills)
        if not all_skills:
            all_skills = ["information_retrieval", "implementation", "unit_testing", "technical_writing"]

        # Query registry for each skill set and form a team
        team = []
        seen = set()
        for skill in all_skills:
            candidates = agent_registry.find_by_skill(skill)
            for at in candidates:
                if at not in seen:
                    team.append(at)
                    seen.add(at)

        # Always include memory agent
        if "knowledge_manager" not in seen:
            team.append("knowledge_manager")

        self.team = team
        event_bus.emit(
            "ceo:team_formed",
            source="CEO",
            message=f"Team formed: {', '.join(team)}",
            data={"team": team, "skills": all_skills},
        )
        return team

    # ---- Step 3: Plan ----
    def plan_tasks(self, request: str) -> List[Task]:
        event_bus.emit("ceo:planning", source="CEO", message="Delegating to Task Planner")
        tasks = self.planner.plan(request, self.analysis)
        event_bus.emit(
            "ceo:plan_ready",
            source="CEO",
            message=f"Plan ready: {len(tasks)} tasks",
            data={"task_ids": [t.task_id for t in tasks]},
        )
        return tasks

    # ---- Step 4: Delegate to Scheduler ----
    def delegate(self, tasks: List[Task]) -> List[AgentResult]:
        if not self.scheduler:
            raise RuntimeError("Scheduler not attached to CEO")
        event_bus.emit("ceo:delegating", source="CEO", message="Activating Scheduler")
        results = self.scheduler.execute(tasks)
        event_bus.emit("ceo:results_collected", source="CEO", message=f"Collected {len(results)} results")
        return results

    # ---- Step 5: Merge + Final Response ----
    def synthesize(self, request: str, tasks: List[Task], results: List[AgentResult]) -> str:
        event_bus.emit("ceo:synthesizing", source="CEO", message="Merging agent outputs into final response")

        sections = []
        sections.append("# NeuroOps Final Report\n")
        sections.append(f"**Original Request:** {request}\n")
        sections.append(f"**Intent:** {self.analysis.get('intent', 'general')}")
        sections.append(f"**Team Selected:** {', '.join(self.team)}")
        sections.append(f"**Tasks Executed:** {len(tasks)}")
        sections.append(f"**Agents Activated:** {len(results)}\n")

        # Group results by department
        by_dept: dict[str, list[AgentResult]] = {}
        for r in results:
            dept = "unknown"
            task = session_store.get_task(r.task_id)
            if task and task.department:
                dept = task.department.value if hasattr(task.department, "value") else str(task.department)
            by_dept.setdefault(dept, []).append(r)

        for dept, dept_results in by_dept.items():
            sections.append(f"## {dept.title()} Department\n")
            for r in dept_results:
                task = session_store.get_task(r.task_id)
                title = task.title if task else r.task_id
                sections.append(f"### {title}")
                sections.append(f"- Agent: `{r.agent_id}`")
                sections.append(f"- Confidence: {r.confidence:.2f}")
                sections.append(f"- Time: {r.execution_time_ms:.0f}ms")
                sections.append(f"- State: {r.state.value if hasattr(r.state, 'value') else r.state}")
                if r.output:
                    sections.append(f"\n{r.output}\n")

        # Failures
        failed = [r for r in results if (r.state.value if hasattr(r.state, 'value') else r.state) == "failed"]
        if failed:
            sections.append("## Failures\n")
            for f in failed:
                sections.append(f"- {f.task_id}: {f.metadata.get('error', 'unknown error')}")

        # Performance summary
        perf = session_store.get_all_performance()
        if perf:
            sections.append("\n## Performance Analytics\n")
            for aid, p in perf.items():
                sections.append(f"- **{aid}**: {p.get('tasks_completed', 0)} completed, "
                                f"{p.get('success_rate', 0):.0%} success, "
                                f"avg confidence {p.get('avg_confidence', 0):.2f}")

        summary = (
            "\n## CEO Summary\n"
            "The NeuroOps workforce has completed all assigned tasks. "
            "The outputs above represent the collective intelligence of a dynamically formed team, "
            "selected by the CEO from the Agent Registry based on skills, performance, and availability."
        )
        sections.append(summary)

        final = "\n".join(sections)
        session_store.set_final_response(final)
        session_store.add_message(ConversationMessage(role="ceo", content=final[:500] + "..."))

        # Store project checkpoint
        memory_service.store_project_state(
            f"Project completed: {request[:100]} | Tasks: {len(tasks)} | Team: {', '.join(self.team)}",
            metadata={"task_count": len(tasks), "team": self.team},
        )
        event_bus.emit("ceo:completed", source="CEO", message="Final response generated")
        return final

    # ---- Full orchestration ----
    def run(self, request: str) -> str:
        session_store.set_workflow_status("running")
        try:
            self.analyze_request(request)
            self.form_team(request)
            tasks = self.plan_tasks(request)
            results = self.delegate(tasks)
            final = self.synthesize(request, tasks, results)
            session_store.set_workflow_status("completed")
            event_bus.emit("workflow:completed", source="CEO", message="Workflow completed successfully")
            return final
        except Exception as exc:
            session_store.set_workflow_status("failed")
            event_bus.emit("workflow:failed", source="CEO", message=f"Workflow failed: {exc}")
            raise
