import os
from typing import List, Optional, Set
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

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

# Default module state: WhatsApp is disabled by default until explicitly enabled
_DEFAULT_MODULE_STATES: dict[str, bool] = {
    "whatsapp": False,
}


def get_disabled_modules() -> Set[str]:
    """Return the normalized set of module names explicitly disabled via DISABLED_MODULES."""
    raw = os.getenv("DISABLED_MODULES", "")
    if not raw:
        return set()
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def is_module_enabled(module_name: str) -> bool:
    """Return True if a module is enabled, honoring DISABLED_MODULES and ENABLE_<MODULE>."""
    norm = module_name.strip().lower()
    if not norm:
        return False

    disabled = get_disabled_modules()
    if norm in disabled or (norm == "webhooks" and "whatsapp" in disabled):
        return False

    env_key = f"ENABLE_{norm.upper()}"
    raw_flag = os.getenv(env_key)
    if raw_flag is not None and raw_flag.strip() != "":
        val = raw_flag.strip().lower()
        if val in ("1", "true", "yes", "on"):
            return True
        if val in ("0", "false", "no", "off"):
            return False

    return _DEFAULT_MODULE_STATES.get(norm, True)


def is_production() -> bool:
    """Return True when the app is running in a production‑like environment."""
    return os.getenv("FLASK_ENV", "development").lower() == "production"


def mask_chat_id(chat_id: int) -> str:
    """Return a masked representation of a chat id, showing only the last 4 digits."""
    s = str(chat_id)
    return "*" * max(len(s) - 4, 0) + s[-4:]


def validate_production_config() -> None:
    """Fail startup if critical env vars are missing in production."""
    if not is_production():
        return
    missing = []
    if not (os.getenv("GITHUB_WEBHOOK_SECRET") or GITHUB_WEBHOOK_SECRET):
        missing.append("GITHUB_WEBHOOK_SECRET")
    if not (os.getenv("CRON_SECRET") or CRON_SECRET):
        missing.append("CRON_SECRET")
    if not (os.getenv("TOKEN") or TOKEN):
        missing.append("TOKEN")
    if not (os.getenv("X_API_KEY") or os.getenv("GAMMA_MOBILE_API_KEY")):
        missing.append("X_API_KEY")
    if is_module_enabled("whatsapp") and not os.getenv("WHATSAPP_WEBHOOK_SECRET"):
        missing.append("WHATSAPP_WEBHOOK_SECRET")
    if missing:
        raise RuntimeError(
            f"Variables de entorno requeridas en producción: {', '.join(missing)}"
        )
