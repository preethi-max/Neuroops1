"""NeuroOps Flask application entry point.

Serves the frontend dashboard and REST API, with real-time event
streaming over Flask-SocketIO.
"""
import os

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

from config import get_config
from core.event_bus import event_bus
from utils import setup_logging, logger

from api import api_bp


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "frontend")


def create_app():
    config = get_config()
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path="",
    )
    app.config.from_object(config)

    socketio = SocketIO(
        app,
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE", "threading"),
        cors_allowed_origins="*",
    )
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(api_bp)

    # Inject socketio into the event bus for real-time broadcasts
    event_bus.set_socketio(socketio)

    # Serve frontend index
    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # Socket.IO events
    @socketio.on("connect")
    def handle_connect():
        logger.info("client connected")
        socketio.emit("server:hello", {"message": "connected to NeuroOps"})

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.info("client disconnected")

    @socketio.on("client:ping")
    def handle_ping(data):
        socketio.emit("server:pong", {"echo": data})

    return app, socketio


def main():
    setup_logging()
    app, socketio = create_app()
    port = int(os.environ.get("PORT", 5000))
    logger.info("NeuroOps starting on port %s", port)
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
