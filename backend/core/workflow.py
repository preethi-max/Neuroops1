"""NeuroOps LangGraph workflow (Phase 3).

Defines the state graph that orchestrates the full pipeline:

  User Request
    -> CEO Agent (analyze)
    -> Agent Registry (query + form team)
    -> Task Planner (plan)
    -> Scheduler (select best agents + execute)
    -> AI Agents (work)
    -> Memory System (store results)
    -> Result Collection
    -> CEO Agent (synthesize)
    -> Final Response

Uses LangGraph's StateGraph. Falls back to a sequential runner if
langgraph is not installed.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from core.ceo_agent import CEOAgent
from core.event_bus import event_bus
from core.scheduler_service import SchedulerService
from core.storage import session_store


class WorkflowState(TypedDict, total=False):
    request: str
    analysis: Dict[str, Any]
    team: List[str]
    tasks: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    final_response: str
    status: str
    error: Optional[str]


class NeuroOpsWorkflow:
    """Wraps the LangGraph state graph + a fallback sequential runner."""

    def __init__(self, max_workers: int = 4):
        self.scheduler = SchedulerService(max_workers=max_workers)
        self.ceo = CEOAgent(scheduler=self.scheduler)
        self._graph = None
        self._build_graph()

    def _build_graph(self):
        try:
            from langgraph.graph import StateGraph, END
        except ImportError:
            self._graph = None
            return

        g = StateGraph(WorkflowState)

        g.add_node("analyze", self._node_analyze)
        g.add_node("form_team", self._node_form_team)
        g.add_node("plan", self._node_plan)
        g.add_node("schedule", self._node_schedule)
        g.add_node("collect", self._node_collect)
        g.add_node("synthesize", self._node_synthesize)

        g.set_entry_point("analyze")
        g.add_edge("analyze", "form_team")
        g.add_edge("form_team", "plan")
        g.add_edge("plan", "schedule")
        g.add_edge("schedule", "collect")
        g.add_edge("collect", "synthesize")
        g.add_edge("synthesize", END)

        self._graph = g.compile()

    # ---- LangGraph nodes ----
    def _node_analyze(self, state: WorkflowState) -> WorkflowState:
        analysis = self.ceo.analyze_request(state["request"])
        return {"analysis": analysis}

    def _node_form_team(self, state: WorkflowState) -> WorkflowState:
        team = self.ceo.form_team(state["request"])
        return {"team": team}

    def _node_plan(self, state: WorkflowState) -> WorkflowState:
        tasks = self.ceo.plan_tasks(state["request"])
        return {"tasks": [t.to_dict() for t in tasks]}

    def _node_schedule(self, state: WorkflowState) -> WorkflowState:
        from core import Task
        task_dicts = state.get("tasks", [])
        tasks = []
        for td in task_dicts:
            t = session_store.get_task(td["task_id"])
            if t:
                tasks.append(t)
        results = self.ceo.delegate(tasks)
        return {"results": [r.to_dict() for r in results]}

    def _node_collect(self, state: WorkflowState) -> WorkflowState:
        event_bus.emit("workflow:collecting", source="Workflow", message="Collecting agent results")
        return state

    def _node_synthesize(self, state: WorkflowState) -> WorkflowState:
        from core import AgentResult, AgentState, Task
        task_dicts = state.get("tasks", [])
        result_dicts = state.get("results", [])
        tasks = [session_store.get_task(td["task_id"]) for td in task_dicts if session_store.get_task(td["task_id"])]
        results = []
        for rd in result_dicts:
            results.append(AgentResult(
                agent_id=rd["agent_id"],
                task_id=rd["task_id"],
                output=rd["output"],
                confidence=rd["confidence"],
                logs=rd.get("logs", []),
                execution_time_ms=rd.get("execution_time_ms", 0),
                state=AgentState(rd.get("state", "completed")),
                metadata=rd.get("metadata", {}),
            ))
        final = self.ceo.synthesize(state["request"], tasks, results)
        return {"final_response": final, "status": "completed"}

    # ---- Public entry point ----
    def run(self, request: str) -> str:
        session_store.set_workflow_status("running")
        event_bus.emit("workflow:started", source="Workflow", message="NeuroOps workflow started")

        if self._graph is not None:
            try:
                result = self._graph.invoke({"request": request})
                session_store.set_workflow_status("completed")
                return result.get("final_response", "")
            except Exception as exc:
                session_store.set_workflow_status("failed")
                event_bus.emit("workflow:failed", source="Workflow", message=f"LangGraph error: {exc}")
                raise

        # Fallback: sequential runner
        try:
            final = self.ceo.run(request)
            session_store.set_workflow_status("completed")
            return final
        except Exception as exc:
            session_store.set_workflow_status("failed")
            event_bus.emit("workflow:failed", source="Workflow", message=f"Workflow error: {exc}")
            raise


# Singleton workflow instance
neuroops_workflow: Optional[NeuroOpsWorkflow] = None


def get_workflow() -> NeuroOpsWorkflow:
    global neuroops_workflow
    if neuroops_workflow is None:
        neuroops_workflow = NeuroOpsWorkflow()
    return neuroops_workflow
