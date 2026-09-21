import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from app_queue import worker


@pytest.fixture(autouse=True)
def clean_queue():
    conn = worker.get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM queue WHERE chat_id = 88888")
    finally:
        conn.close()
    yield
    conn = worker.get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM queue WHERE chat_id = 88888")
    finally:
        conn.close()


def test_enqueue_and_pending_count():
    chat_id = 88888
    job_id = worker.enqueue(chat_id, "test_op", {"amount": 100})
    assert job_id > 0
    assert worker.get_pending_count() >= 1


def test_procesar_trabajo_exitoso():
    chat_id = 88888
    job_id = worker.enqueue(chat_id, "registrar_movimiento", {"total": 50000})

    mock_bot = MagicMock()

    with patch("app_queue.worker.despachar_trabajo") as mock_dispatch:
        procesados = worker.procesar_trabajos_pendientes(mock_bot)
        assert procesados >= 1
        mock_dispatch.assert_called_with(
            mock_bot, "registrar_movimiento", {"total": 50000}, chat_id
        )

    # Check status is completado
    conn = worker.get_connection()
    try:
        row = conn.execute(
            "SELECT estado FROM queue WHERE id = ?", (job_id,)
        ).fetchone()
        assert row["estado"] == "completado"
    finally:
        conn.close()


def test_sync_fallback():
    chat_id = 88888
    mock_bot = MagicMock()

    with patch("app_queue.worker.despachar_trabajo") as mock_dispatch:
        res = worker.enqueue(
            chat_id,
            "create_debt",
            {"concepto": "test"},
            sync_fallback=True,
            bot=mock_bot,
        )
        assert res == 0
        mock_dispatch.assert_called_once_with(
            mock_bot, "create_debt", {"concepto": "test"}, chat_id
        )


def test_retry_on_failure():
    chat_id = 88888
    job_id = worker.enqueue(chat_id, "fail_op", {"foo": "bar"})

    mock_bot = MagicMock()

    with patch(
        "app_queue.worker.despachar_trabajo", side_effect=RuntimeError("Fallo simulado")
    ):
        procesados = worker.procesar_trabajos_pendientes(mock_bot)
        assert procesados == 0

    conn = worker.get_connection()
    try:
        row = conn.execute(
            "SELECT estado, reintentos FROM queue WHERE id = ?", (job_id,)
        ).fetchone()
        assert row["estado"] == "pendiente"
        assert row["reintentos"] == 1
    finally:
        conn.close()
