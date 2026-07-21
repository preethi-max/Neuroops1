"""NeuroOps application entry point.

Wires Flask + Flask-SocketIO + SQLAlchemy, registers blueprints,
initializes the SQLite database, serves the frontend, and starts
the scheduler background thread.
"""
import os
import subprocess
import sys

# Make the backend directory importable when run directly.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _ensure_deps():
    """Install requirements if Flask is missing (fresh deployment env)."""
    try:
        import flask  # noqa: F401
        return
    except ImportError:
        pass
    reqs = os.path.join(BACKEND_DIR, "requirements.txt")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", reqs]
    )


_ensure_deps()

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy

from config import get_config
from database import init_db, shutdown_session
from utils import setup_logging, emit_event, logger
from core.event_bus import event_bus

from api import api_bp, workflow_bp
from agents import agents_bp
from scheduler import scheduler_bp, start_scheduler


def create_app():
    config = get_config()
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(BACKEND_DIR), "frontend"),
        static_url_path="",
    )
    app.config.from_object(config)

    socketio = SocketIO(
        app,
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "threading"),
        cors_allowed_origins="*",
    )

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(agents_bp)
    app.register_blueprint(scheduler_bp)

    # Inject socketio into the event bus for real-time broadcasts
    event_bus.set_socketio(socketio)

    # Initialize database (Phase 1 — still used by legacy endpoints)
    init_db()
    logger.info("database initialized at %s", app.config["SQLALCHEMY_DATABASE_URI"])

    # Teardown
    @app.teardown_appcontext
    def remove_session(exception=None):
        shutdown_session(exception)

    # Serve frontend index
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # Socket.IO events
    @socketio.on("connect")
    def handle_connect():
        logger.info("client connected: %s", request.sid if False else "anon")
        emit("server:hello", {"message": "connected to NeuroOps"})

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info("client disconnected")

    @socketio.on("client:ping")
    def handle_ping(data):
        emit("server:pong", {"echo": data})

    return app, socketio


# request import used inside event handlers
from flask import request  # noqa: E402


def main():
    setup_logging()
    app, socketio = create_app()

    # Start scheduler background thread
    interval = app.config.get("SCHEDULER_INTERVAL_SECONDS", 10)
    start_scheduler(socketio, interval=interval)

    port = int(os.environ.get("PORT", 5000))
    logger.info("NeuroOps starting on port %s", port)
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
