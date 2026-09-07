import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# Load environment variables with minimal validation
TOKEN: str = os.getenv("TOKEN", "")
# CHAT_ID can be a comma‑separated list of ints
_RAW_CHAT_ID = os.getenv("CHAT_ID", "")
if _RAW_CHAT_ID:
    try:
        CHAT_IDS: List[int] = [int(part.strip()) for part in _RAW_CHAT_ID.split(",")]
    except ValueError:
        raise RuntimeError(
            "Invalid CHAT_ID – must be a comma‑separated list of integers"
        )
else:
    CHAT_IDS = []

GITHUB_WEBHOOK_SECRET: Optional[str] = os.getenv("GITHUB_WEBHOOK_SECRET")
CRON_SECRET: Optional[str] = os.getenv("CRON_SECRET")

# Simple flag to differentiate dev vs prod (defaults to development)
FLASK_ENV: str = os.getenv("FLASK_ENV", "development").lower()


def is_production() -> bool:
    """Return True when the app is running in a production‑like environment."""
    return FLASK_ENV == "production"


def mask_chat_id(chat_id: int) -> str:
    """Return a masked representation of a chat id, showing only the last 4 digits."""
    s = str(chat_id)
    return "*" * max(len(s) - 4, 0) + s[-4:]
