"""NeuroOps Phase 3 REST API blueprint.

Endpoints:
  POST /api/workflow/submit       - Submit a request to the autonomous workflow
  GET  /api/workflow/tasks         - Get current tasks
  GET  /api/workflow/agents        - Get agent states + registry
  GET  /api/workflow/timeline      - Get timeline events
  GET  /api/workflow/session       - Get session info
  POST /api/workflow/reset         - Reset the session
  GET  /api/registry               - List all registered agents
  GET  /api/registry/<agent_type>  - Get a specific agent's details
  GET  /api/memory                 - Get memory entries (filter by type)
  POST /api/memory                 - Store a memory entry
  GET  /api/memory/search          - Search memory by keyword
  GET  /api/approvals              - Get pending approvals
  POST /api/approvals/<id>/resolve - Resolve an approval (approve/reject/modify)
  GET  /api/analytics              - Get performance analytics
  GET  /api/health                 - Health check
"""
from __future__ import annotations

import threading

from flask import Blueprint, jsonify, request

from agents.registry import agent_registry
from core.approval_service import approval_service
from core.event_bus import event_bus
from core.memory_service import memory_service
from core.performance_analytics import performance_analytics
from core.storage import session_store
from core.workflow import get_workflow
from utils import handle_errors

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health", methods=["GET"])
@handle_errors
def health():
    return jsonify({"status": "ok", "service": "neuroops", "phase": 3})


# ---- Workflow ----

@api_bp.route("/workflow/submit", methods=["POST"])
@handle_errors
def submit_request():
    data = request.get_json(force=True)
    user_request = data.get("request", "").strip()
    if not user_request:
        return jsonify({"error": "Request body is required"}), 400

    event_bus.emit("workflow:request_received", source="API", message=f"New request: {user_request[:80]}")

    def _run():
        try:
            get_workflow().run(user_request)
        except Exception as exc:
            event_bus.emit("workflow:failed", source="API", message=f"Workflow exception: {exc}")

    thread = threading.Thread(target=_run, daemon=True, name="neuroops-workflow")
    thread.start()

    return jsonify({
        "status": "accepted",
        "session_id": session_store.session_id,
        "trace_id": session_store.trace_id,
        "message": "Workflow started. Listen to Socket.IO 'neuroops:event' for real-time updates.",
    }), 202


@api_bp.route("/workflow/tasks", methods=["GET"])
@handle_errors
def get_tasks():
    return jsonify([t.to_dict() for t in session_store.get_all_tasks()])


@api_bp.route("/workflow/agents", methods=["GET"])
@handle_errors
def get_agent_states():
    return jsonify({
        "states": agent_registry.all_states(),
        "registry": agent_registry.list_agents(),
    })


@api_bp.route("/workflow/timeline", methods=["GET"])
@handle_errors
def get_timeline():
    return jsonify([e.to_dict() for e in session_store.get_timeline()])


@api_bp.route("/workflow/session", methods=["GET"])
@handle_errors
def get_session():
    return jsonify({
        "session": session_store.get_session(),
        "conversation": [m.to_dict() for m in session_store.get_conversation()],
        "task_graph": session_store.get_task_graph(),
    })


@api_bp.route("/workflow/reset", methods=["POST"])
@handle_errors
def reset_session():
    session_store.reset()
    event_bus.emit("workflow:reset", source="API", message="Session reset")
    return jsonify({"status": "reset", "session_id": session_store.session_id})


# ---- Agent Registry ----

@api_bp.route("/registry", methods=["GET"])
@handle_errors
def list_registry():
    return jsonify(agent_registry.list_agents())


@api_bp.route("/registry/<agent_type>", methods=["GET"])
@handle_errors
def get_registry_agent(agent_type):
    spec = agent_registry.get_agent_spec(agent_type)
    if not spec:
        return jsonify({"error": "agent type not found"}), 404
    return jsonify(spec)


# ---- Memory ----

@api_bp.route("/memory", methods=["GET"])
@handle_errors
def get_memory():
    memory_type = request.args.get("type")
    agent_id = request.args.get("agent_id")
    entries = session_store.get_memory(memory_type=memory_type, agent_id=agent_id)
    return jsonify([m.to_dict() for m in entries])


@api_bp.route("/memory", methods=["POST"])
@handle_errors
def store_memory():
    data = request.get_json(force=True)
    memory_type = data.get("memory_type", "semantic")
    content = data.get("content", "")
    agent_id = data.get("agent_id")
    if memory_type == "episodic":
        entry = memory_service.store_episode(content, agent_id=agent_id, metadata=data.get("metadata"))
    elif memory_type == "semantic":
        entry = memory_service.store_knowledge(content, metadata=data.get("metadata"))
    elif memory_type == "project":
        entry = memory_service.store_project_state(content, project_id=data.get("project_id"), metadata=data.get("metadata"))
    elif memory_type == "agent":
        entry = memory_service.store_agent_memory(agent_id or "unknown", content, metadata=data.get("metadata"))
    else:
        return jsonify({"error": "invalid memory_type"}), 400
    return jsonify(entry.to_dict()), 201


@api_bp.route("/memory/search", methods=["GET"])
@handle_errors
def search_memory():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "query parameter 'q' is required"}), 400
    results = memory_service.search_memory(q)
    return jsonify([m.to_dict() for m in results])


# ---- Approvals ----

@api_bp.route("/approvals", methods=["GET"])
@handle_errors
def get_approvals():
    return jsonify([a.to_dict() for a in session_store.get_pending_approvals()])


@api_bp.route("/approvals/<approval_id>/resolve", methods=["POST"])
@handle_errors
def resolve_approval(approval_id):
    data = request.get_json(force=True)
    decision = data.get("decision")  # approved | rejected | modification
    notes = data.get("notes")
    if decision not in ("approved", "rejected", "modification"):
        return jsonify({"error": "decision must be approved, rejected, or modification"}), 400
    req = approval_service.resolve(approval_id, decision, notes)
    if not req:
        return jsonify({"error": "approval not found"}), 404
    return jsonify(req.to_dict())


# ---- Analytics ----

@api_bp.route("/analytics", methods=["GET"])
@handle_errors
def get_analytics():
    return jsonify({
        "system": performance_analytics.get_system_stats(),
        "agents": performance_analytics.get_all_agent_stats(),
    })
