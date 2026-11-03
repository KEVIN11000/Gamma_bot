import pytest
from app_queue import worker
from adapters.notifications.mock_adapter import MockNotificationAdapter
from services.notification_dispatcher import NotificationDispatcher


@pytest.fixture(autouse=True)
def clean_test_jobs():
    conn = worker.get_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM queue WHERE recipient_id IN ('+595981111222', 'usr_mobile_99', 'sync_rec_1')"
            )
    finally:
        conn.close()
    yield
    conn = worker.get_connection()
    try:
        with conn:
            conn.execute(
                "DELETE FROM queue WHERE recipient_id IN ('+595981111222', 'usr_mobile_99', 'sync_rec_1')"
            )
    finally:
        conn.close()


def test_enqueue_multichannel_custom_channel():
    """Verifies that enqueue records alphanumeric recipient_id and arbitrary channel correctly."""
    rec_id = "+595981111222"
    job_id = worker.enqueue(rec_id, "op_custom", {"amount": 500}, channel="whatsapp")
    assert job_id > 0

    conn = worker.get_connection()
    try:
        row = conn.execute(
            "SELECT recipient_id, channel, estado FROM queue WHERE id = ?",
            (job_id,),
        ).fetchone()
        assert row["recipient_id"] == rec_id
        assert row["channel"] == "whatsapp"
        assert row["estado"] == "pendiente"
    finally:
        conn.close()


def test_process_multichannel_with_dispatcher():
    """Verifies that procesar_trabajos_pendientes routes jobs to registered channel adapters."""
    dispatcher = NotificationDispatcher(default_channel="telegram")
    wa_adapter = MockNotificationAdapter()
    mob_adapter = MockNotificationAdapter()
    dispatcher.register_adapter("whatsapp", wa_adapter)
    dispatcher.register_adapter("mobile", mob_adapter)

    wa_rec = "+595981111222"
    mob_rec = "usr_mobile_99"

    job_wa = worker.enqueue(wa_rec, "op_wa", {"key": "wa_val"}, channel="whatsapp")
    job_mob = worker.enqueue(mob_rec, "op_mob", {"key": "mob_val"}, channel="mobile")

    procesados = worker.procesar_trabajos_pendientes(dispatcher=dispatcher)
    assert procesados >= 2

    # Verify WhatsApp adapter got its message
    assert len(wa_adapter.sent_messages) >= 1
    wa_msg = [m for m in wa_adapter.sent_messages if m.recipient_id == wa_rec][0]
    assert "op_wa" in wa_msg.message

    # Verify Mobile adapter got its message
    assert len(mob_adapter.sent_messages) >= 1
    mob_msg = [m for m in mob_adapter.sent_messages if m.recipient_id == mob_rec][0]
    assert "op_mob" in mob_msg.message

    # Verify statuses in DB
    conn = worker.get_connection()
    try:
        status_wa = conn.execute(
            "SELECT estado FROM queue WHERE id = ?", (job_wa,)
        ).fetchone()["estado"]
        status_mob = conn.execute(
            "SELECT estado FROM queue WHERE id = ?", (job_mob,)
        ).fetchone()["estado"]
        assert status_wa == "completado"
        assert status_mob == "completado"
    finally:
        conn.close()


def test_multichannel_sync_fallback_with_custom_notifier():
    """Verifies synchronous fallback using a custom INotificationPort instance."""
    mock_notifier = MockNotificationAdapter()
    rec_id = "sync_rec_1"

    res = worker.enqueue(
        rec_id,
        "op_sync",
        {"data": 123},
        sync_fallback=True,
        notifier=mock_notifier,
    )
    assert res == 0
    assert len(mock_notifier.sent_messages) == 1
    assert mock_notifier.sent_messages[0].recipient_id == rec_id
    assert "op_sync" in mock_notifier.sent_messages[0].message


def test_despachar_trabajo_with_notification_port():
    """Verifies that despachar_trabajo operates cleanly when passed an INotificationPort."""
    mock_notifier = MockNotificationAdapter()
    worker.despachar_trabajo(
        mock_notifier,
        "unknown_custom_op",
        {"test": True},
        "+595981111222",
    )
    assert len(mock_notifier.sent_messages) == 1
    assert mock_notifier.sent_messages[0].recipient_id == "+595981111222"
    assert "unknown_custom_op" in mock_notifier.sent_messages[0].message


def test_create_default_dispatcher_auto_registers_whatsapp(monkeypatch):
    """Verifies that create_default_dispatcher auto-registers whatsapp adapter when env var is present."""
    monkeypatch.delenv("WHATSAPP_API_URL", raising=False)
    disp_without = worker.create_default_dispatcher()
    assert not disp_without.has_channel("whatsapp")

    monkeypatch.setenv("WHATSAPP_API_URL", "http://localhost:8080")
    disp_with = worker.create_default_dispatcher()
    assert disp_with.has_channel("whatsapp")


def test_whatsapp_end_to_end_worker_dispatch(monkeypatch):
    """Verifies full lifecycle of enqueued WhatsApp message processed by default dispatcher."""
    monkeypatch.setenv("WHATSAPP_API_URL", "http://test-wa:8080")
    monkeypatch.setenv("WHATSAPP_API_KEY", "tok_123")
    monkeypatch.setenv("WHATSAPP_INSTANCE_NAME", "inst_test")

    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    wa_rec = "+595981111222"
    job_id = worker.enqueue(
        wa_rec,
        "procesar_mensaje_whatsapp",
        {"text": "consulta estado", "push_name": "Maria"},
        channel="whatsapp",
    )
    assert job_id > 0

    with patch("requests.Session.post", return_value=mock_resp) as mock_post:
        procesados = worker.procesar_trabajos_pendientes()
        assert procesados >= 1

        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        json_data = mock_post.call_args[1]["json"]

        assert url == "http://test-wa:8080/message/sendText/inst_test"
        assert json_data["number"] == "595981111222"
        assert "Maria" in json_data["text"]
        assert "consulta estado" in json_data["text"]

    conn = worker.get_connection()
    try:
        row = conn.execute(
            "SELECT estado FROM queue WHERE id = ?", (job_id,)
        ).fetchone()
        assert row["estado"] == "completado"
    finally:
        conn.close()
