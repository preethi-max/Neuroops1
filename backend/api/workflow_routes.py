"""NeuroOps Phase 2 workflow API blueprint.

REST endpoints:
  POST /api/workflow/submit   - Submit a request to the autonomous workflow
  GET  /api/workflow/tasks     - Get current tasks
  GET  /api/workflow/agents    - Get agent states
  GET  /api/workflow/timeline  - Get timeline events
  GET  /api/workflow/session   - Get session info
  POST /api/workflow/reset     - Reset the session
  GET  /api/workflow/registry  - List all available agent types
"""
from __future__ import annotations

import threading

from flask import Blueprint, jsonify, request

from core.event_bus import event_bus
from core.storage import session_store
from core.workflow import get_workflow
from agents.registry import all_agent_metadata
from utils import handle_errors

workflow_bp = Blueprint("workflow", __name__, url_prefix="/api/workflow")


@workflow_bp.route("/submit", methods=["POST"])
@handle_errors
def submit_request():
    data = request.get_json(force=True)
    user_request = data.get("request", "").strip()
    if not user_request:
        return jsonify({"error": "Request body is required"}), 400

    event_bus.emit("workflow:request_received", source="API", message=f"New request: {user_request[:80]}")

    # Run the workflow in a background thread so events stream in real time.
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
        "message": "Workflow started. Listen to Socket.IO 'neuroops:event' for real-time updates.",
    }), 202


@workflow_bp.route("/tasks", methods=["GET"])
@handle_errors
def get_tasks():
    return jsonify([t.to_dict() for t in session_store.get_all_tasks()])


@workflow_bp.route("/agents", methods=["GET"])
@handle_errors
def get_agent_states():
    return jsonify({
        "states": session_store.get_all_agent_states(),
        "registry": all_agent_metadata(),
    })


@workflow_bp.route("/timeline", methods=["GET"])
@handle_errors
def get_timeline():
    return jsonify([e.to_dict() for e in session_store.get_timeline()])


@workflow_bp.route("/session", methods=["GET"])
@handle_errors
def get_session():
    return jsonify({
        "session": session_store.get_session(),
        "conversation": [m.to_dict() for m in session_store.get_conversation()],
        "memory_summaries": session_store.get_memory_summaries(),
        "task_graph": session_store.get_task_graph(),
    })


@workflow_bp.route("/reset", methods=["POST"])
@handle_errors
def reset_session():
    session_store.reset()
    event_bus.emit("workflow:reset", source="API", message="Session reset")
    return jsonify({"status": "reset", "session_id": session_store.session_id})


@workflow_bp.route("/registry", methods=["GET"])
@handle_errors
def get_registry():
    return jsonify(all_agent_metadata())
