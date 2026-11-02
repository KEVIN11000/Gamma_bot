from __future__ import annotations

import json
from pathlib import Path

from api.v1 import v1_bp

mobile_api = v1_bp

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORTES_DIR = BASE_DIR / "reportes"
AVISOS_FILE = BASE_DIR / "avisos.json"
TICKETS_FILE = DATA_DIR / "tickets.json"

# Almacén de deduplicación e idempotencia (client_id -> timestamp)
_PROCESSED_CLIENT_IDS: dict[str, float] = {}


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    if not TICKETS_FILE.exists():
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


_ensure_dirs()

__all__ = [
    "mobile_api",
    "v1_bp",
    "BASE_DIR",
    "DATA_DIR",
    "REPORTES_DIR",
    "AVISOS_FILE",
    "TICKETS_FILE",
    "_PROCESSED_CLIENT_IDS",
    "_ensure_dirs",
]
