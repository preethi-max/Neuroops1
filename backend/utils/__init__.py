"""NeuroOps utility helpers."""
import logging
from functools import wraps

logger = logging.getLogger("neuroops")


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def handle_errors(fn):
    """Decorator returning JSON error responses instead of 500s."""
    from flask import jsonify

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.exception("error in %s", fn.__name__)
            return jsonify({"error": str(exc)}), 500

    return wrapper
