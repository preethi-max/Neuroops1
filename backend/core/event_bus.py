"""NeuroOps event bus.

Central emitter that records timeline events in the SessionStore and
broadcasts them over Flask-SocketIO. Decouples workflow/agent logic from
the transport layer.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from core import TimelineEvent
from core.storage import session_store
from utils import logger


class EventBus:
    """Records + broadcasts timeline events."""

    def __init__(self, socketio=None):
        self._socketio = socketio

    def set_socketio(self, socketio):
        self._socketio = socketio

    def emit(self, event_type: str, source: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Record a timeline event and broadcast it via Socket.IO."""
        event = TimelineEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            source=source,
            message=message,
            data=data or {},
        )
        session_store.add_event(event)
        payload = event.to_dict()
        if self._socketio is not None:
            try:
                self._socketio.emit("neuroops:event", payload)
            except Exception as exc:  # pragma: no cover
                logger.error("event bus emit failed: %s", exc)
        logger.info("[event] %s/%s: %s", source, event_type, message)
        return payload


# Singleton event bus. app.py injects the socketio instance.
event_bus = EventBus()
