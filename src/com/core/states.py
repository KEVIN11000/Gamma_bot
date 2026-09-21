"""State machine with persistent SQLite storage and in-memory fallback for Gamma bot.

Designed to prevent state volatility across WSGI/Flask worker recycles.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from logger_config import setup_logger

logger = setup_logger("states")

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DB_PATH = BASE_DIR / "cola.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


_memory_fallback: dict[int, dict[str, Any]] = {}
_states = _memory_fallback


def _init_states_table() -> None:
    try:
        conn = _get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_states (
                        user_id INTEGER PRIMARY KEY,
                        estado TEXT NOT NULL,
                        datos_json TEXT NOT NULL,
                        updated_at INTEGER NOT NULL
                    )
                    """)
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing user_states table: {e}")


# Initialize table on import
_init_states_table()


def set_state(user_id: int, estado: str, datos: dict[str, Any] | None = None) -> None:
    """Sets the state for a given user in SQLite with memory fallback."""
    if datos is None:
        datos = {}

    # Update in-memory fallback
    _memory_fallback[user_id] = {"estado": estado, "datos": datos}

    try:
        conn = _get_connection()
        try:
            with conn:
                datos_str = json.dumps(datos)
                now = int(time.time())
                conn.execute(
                    """
                    INSERT INTO user_states (user_id, estado, datos_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        estado = excluded.estado,
                        datos_json = excluded.datos_json,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, estado, datos_str, now),
                )
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error persisting state in SQLite for user {user_id}: {e}")


def get_state(user_id: int) -> dict[str, Any] | None:
    """Gets the state for a given user from SQLite, falling back to memory."""
    try:
        conn = _get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT estado, datos_json FROM user_states WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                estado = row["estado"]
                datos = json.loads(row["datos_json"])
                state = {"estado": estado, "datos": datos}
                _memory_fallback[user_id] = state
                return state
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error reading state from SQLite for user {user_id}: {e}")

    return _memory_fallback.get(user_id)


def clear_state(user_id: int) -> None:
    """Clears the state for a given user from SQLite and memory."""
    if user_id in _memory_fallback:
        del _memory_fallback[user_id]

    try:
        conn = _get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error clearing state in SQLite for user {user_id}: {e}")


def has_state(user_id: int) -> bool:
    """Checks if a user has an active state."""
    state = get_state(user_id)
    return state is not None
