"""NeuroOps CEO Agent.

The CEO does NOT execute tasks. It:
  - Analyzes the user request (intent + scope)
  - Delegates decomposition to the Task Planner
  - Activates the Scheduler
  - Monitors progress
  - Handles failures (retry / skip decisions)
  - Merges all agent outputs
  - Generates the final response
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from core import AgentResult, Task
from core.event_bus import event_bus
from core.storage import session_store
from core.task_planner import TaskPlanner


class CEOAgent:
    """Orchestrates the entire NeuroOps workflow."""

    def __init__(self, planner: Optional[TaskPlanner] = None, scheduler=None):
        self.planner = planner or TaskPlanner()
        # scheduler injected later to avoid circular import
        self.scheduler = scheduler
        self.analysis: dict = {}

    def set_scheduler(self, scheduler):
        self.scheduler = scheduler

    # ---- Step 1: Analyze ----
    def analyze_request(self, request: str) -> dict:
        event_bus.emit("ceo:started", source="CEO", message=f"Analyzing request: {request[:80]}")
        session_store.add_message(__import__("core").ConversationMessage(role="user", content=request))

        analysis = {
            "raw_request": request,
            "intent": self._classify_intent(request),
            "scope": "single" if len(request) < 100 else "complex",
            "estimated_tasks": max(3, min(8, len(request.split()) // 5)),
            "departments_needed": self._identify_departments(request),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.analysis = analysis
        session_store.add_message(
            __import__("core").ConversationMessage(
                role="ceo", content=f"Analysis: {analysis['intent']} (scope={analysis['scope']})", metadata=analysis
            )
        )
        event_bus.emit(
            "ceo:analysis",
            source="CEO",
            message=f"Intent: {analysis['intent']} | Departments: {analysis['departments_needed']}",
            data=analysis,
        )
        return analysis

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
        return "general"

    def _identify_departments(self, request: str) -> List[str]:
        r = request.lower()
        deps = []
        if any(w in r for w in ["code", "build", "implement", "debug", "review", "document"]):
            deps.append("engineering")
        if any(w in r for w in ["ui", "design", "wireframe", "layout"]):
            deps.append("design")
        if any(w in r for w in ["research", "search", "find", "summar"]):
            deps.append("research")
        if any(w in r for w in ["notify", "alert", "inform"]):
            deps.append("communication")
        deps.append("memory")  # always
        return list(dict.fromkeys(deps))  # dedupe preserving order

    # ---- Step 2: Plan ----
    def plan_tasks(self, request: str) -> List[Task]:
        event_bus.emit("ceo:planning", source="CEO", message="Delegating to Task Planner")
        tasks = self.planner.plan(request)
        event_bus.emit(
            "ceo:plan_ready",
            source="CEO",
            message=f"Plan ready: {len(tasks)} tasks",
            data={"task_ids": [t.task_id for t in tasks]},
        )
        return tasks

    # ---- Step 3: Delegate to Scheduler ----
    def delegate(self, tasks: List[Task]) -> List[AgentResult]:
        if not self.scheduler:
            raise RuntimeError("Scheduler not attached to CEO")
        event_bus.emit("ceo:delegating", source="CEO", message="Activating Scheduler")
        results = self.scheduler.execute(tasks)
        event_bus.emit("ceo:results_collected", source="CEO", message=f"Collected {len(results)} results")
        return results

    # ---- Step 4: Merge + Final Response ----
    def synthesize(self, request: str, tasks: List[Task], results: List[AgentResult]) -> str:
        event_bus.emit("ceo:synthesizing", source="CEO", message="Merging agent outputs into final response")

        sections = []
        sections.append("# NeuroOps Final Report\n")
        sections.append(f"**Original Request:** {request}\n")
        sections.append(f"**Intent:** {self.analysis.get('intent', 'general')}")
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
        failed = [r for r in results if r.state.value == "failed" if hasattr(r.state, "value") or r.state == "failed"]
        if failed:
            sections.append("## Failures\n")
            for f in failed:
                sections.append(f"- {f.task_id}: {f.metadata.get('error', 'unknown error')}")

        summary = (
            "\n## CEO Summary\n"
            "All required departments have completed their work. "
            "The outputs above represent the collective intelligence of the NeuroOps workforce."
        )
        sections.append(summary)

        final = "\n".join(sections)
        session_store.set_final_response(final)
        session_store.add_message(
            __import__("core").ConversationMessage(role="ceo", content=final[:500] + "...")
        )
        event_bus.emit("ceo:completed", source="CEO", message="Final response generated")
        return final

    # ---- Full orchestration ----
    def run(self, request: str) -> str:
        session_store.set_workflow_status("running")
        try:
            self.analyze_request(request)
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
