import os
from typing import Dict, Any


def load_settings() -> Dict[str, Any]:
    """Carga configuraciones desde variables de entorno."""
    return {
        "telegram_token": os.getenv("TELEGRAM_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "database_url": os.getenv("DATABASE_URL"),
        "postgres_host": os.getenv("POSTGRES_HOST", "localhost"),
        "postgres_port": os.getenv("POSTGRES_PORT", "5432"),
        "postgres_db": os.getenv("POSTGRES_DB", "price_tracker"),
        "postgres_user": os.getenv("POSTGRES_USER", "postgres"),
        "postgres_password": os.getenv("POSTGRES_PASSWORD"),
    }