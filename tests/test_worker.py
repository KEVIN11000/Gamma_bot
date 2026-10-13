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


def test_despachar_generar_reporte_financiero(tmp_path):
    chat_id = 88888
    mock_bot = MagicMock()
    fake_pdf = tmp_path / "reporte_test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 test")

    with patch("logic.financiero.AgenteFinanciero") as mock_agente_cls, patch(
        "logic.pdf_service.PDFService.generar_reporte_generico",
        return_value=(str(fake_pdf), "Reporte generado"),
    ):
        mock_agente = MagicMock()
        mock_agente.preparar_datos_reporte.return_value = ({"datos": True}, None)
        mock_agente_cls.return_value = mock_agente

        worker.despachar_trabajo(
            mock_bot, "generar_reporte", {"tipo": "financiero"}, chat_id
        )

        mock_bot.send_document.assert_called_once()
        args, kwargs = mock_bot.send_document.call_args
        assert args[0] == chat_id
        assert kwargs["caption"] == "📊 Reporte generado"


def test_sync_fallback_failure_notifies_user():
    chat_id = 88888
    mock_bot = MagicMock()

    with patch(
        "app_queue.worker.despachar_trabajo", side_effect=ValueError("Fallo simulado")
    ):
        res = worker.enqueue(
            chat_id,
            "generar_reporte",
            {"tipo": "financiero"},
            sync_fallback=True,
            bot=mock_bot,
        )
        assert res > 0  # Enqueued as fallback in sqlite
        mock_bot.send_message.assert_called_once()
        assert "❌ Ocurrió un error" in mock_bot.send_message.call_args[0][1]
