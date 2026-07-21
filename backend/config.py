"""NeuroOps configuration."""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "neuroops-dev-secret-key")

    # Scheduler
    SCHEDULER_MAX_WORKERS = int(os.environ.get("SCHEDULER_MAX_WORKERS", "4"))
    SCHEDULER_TASK_TIMEOUT = float(os.environ.get("SCHEDULER_TASK_TIMEOUT", "30"))
    SCHEDULER_MAX_RETRIES = int(os.environ.get("SCHEDULER_MAX_RETRIES", "2"))

    # Human-in-the-loop
    APPROVAL_CONFIDENCE_THRESHOLD = float(os.environ.get("APPROVAL_CONFIDENCE_THRESHOLD", "0.5"))

    # Memory
    MEMORY_MAX_ENTRIES = int(os.environ.get("MEMORY_MAX_ENTRIES", "1000"))

    # Model provider (defaults to stub; set env vars to enable real providers)
    MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "stub")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")

    # Flask-SocketIO
    SOCKETIO_ASYNC_MODE = os.environ.get("SOCKETIO_ASYNC_MODE", "threading")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    env = name or os.environ.get("FLASK_ENV", "development")
    return CONFIG_MAP.get(env, DevelopmentConfig)
