import os
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError
from api.schemas import (
    WhatsAppMessageData,
    WhatsAppWebhookEvent,
    WhatsAppWebhookResponse,
)
from app_queue import worker

# Set required env vars BEFORE importing flask_app
os.environ.setdefault("TOKEN", "test_token_123")
os.environ.setdefault("CHAT_ID", "123456")
os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")
os.environ.setdefault("WHATSAPP_WEBHOOK_SECRET", "dev-webhook-secret")

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def clean_webhook_queue():
    conn = worker.get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM queue WHERE channel = 'whatsapp'")
    finally:
        conn.close()
    yield
    conn = worker.get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM queue WHERE channel = 'whatsapp'")
    finally:
        conn.close()


def test_whatsapp_message_data_flat():
    """Verifies that flat dictionary input populates WhatsAppMessageData correctly."""
    data = WhatsAppMessageData(
        remote_jid="595981123456",
        text="Hola bot",
        from_me=False,
        push_name="Kevin",
    )
    assert data.remote_jid == "595981123456"
    assert data.text == "Hola bot"
    assert data.from_me is False
    assert data.push_name == "Kevin"
    assert data.message_type == "conversation"


def test_whatsapp_message_data_nested_evolution_api():
    """Verifies that Evolution API nested structure (key + message) is parsed accurately."""
    raw = {
        "key": {
            "remoteJid": "595981123456@s.whatsapp.net",
            "fromMe": False,
            "id": "MSG_ID_123",
        },
        "pushName": "Kevin Pera",
        "message": {
            "conversation": "Registrar gasto 50000 combustible",
        },
        "messageType": "conversation",
    }
    data = WhatsAppMessageData.model_validate(raw)
    assert data.remote_jid == "595981123456@s.whatsapp.net"
    assert data.from_me is False
    assert data.push_name == "Kevin Pera"
    assert data.text == "Registrar gasto 50000 combustible"


def test_whatsapp_message_data_extended_text_message():
    """Verifies parsing of extendedTextMessage nested payload."""
    raw = {
        "key": {
            "remoteJid": "12036304@g.us",
            "fromMe": True,
        },
        "message": {
            "extendedTextMessage": {
                "text": "Mensaje extendido con enlace",
            }
        },
        "messageType": "extendedTextMessage",
    }
    data = WhatsAppMessageData.model_validate(raw)
    assert data.remote_jid == "12036304@g.us"
    assert data.from_me is True
    assert data.text == "Mensaje extendido con enlace"
    assert data.message_type == "extendedTextMessage"


def test_whatsapp_message_data_document_caption():
    """Verifies fallback extraction of caption for documentMessage."""
    raw = {
        "key": {"remoteJid": "595981111222"},
        "message": {
            "documentMessage": {
                "caption": "Comprobante de pago PDF",
            }
        },
    }
    data = WhatsAppMessageData.model_validate(raw)
    assert data.remote_jid == "595981111222"
    assert data.text == "Comprobante de pago PDF"


def test_whatsapp_webhook_event_parsing():
    """Verifies full WhatsAppWebhookEvent parsing and default instance handling."""
    raw_event = {
        "event": "messages.upsert",
        "instance": "gamma_prod",
        "data": {
            "key": {
                "remoteJid": "595981999888@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {
                "conversation": "Marcar entrada",
            },
        },
    }
    event = WhatsAppWebhookEvent.model_validate(raw_event)
    assert event.event == "messages.upsert"
    assert event.instance == "gamma_prod"
    assert event.data.remote_jid == "595981999888@s.whatsapp.net"
    assert event.data.text == "Marcar entrada"
    assert event.data.from_me is False


def test_whatsapp_webhook_event_validation_errors():
    """Verifies that missing required fields raise ValidationError."""
    # Missing 'event'
    with pytest.raises(ValidationError):
        WhatsAppWebhookEvent.model_validate(
            {"data": {"remote_jid": "123", "text": "test"}}
        )

    # Missing 'remote_jid' inside data
    with pytest.raises(ValidationError):
        WhatsAppWebhookEvent.model_validate(
            {"event": "messages.upsert", "data": {"text": "sin remitente"}}
        )


def test_whatsapp_webhook_response_dto():
    """Verifies default and custom values in WhatsAppWebhookResponse."""
    resp_default = WhatsAppWebhookResponse()
    assert resp_default.status == "ok"
    assert resp_default.job_id is None
    assert resp_default.ignored is False

    resp_custom = WhatsAppWebhookResponse(
        status="enqueued",
        job_id=101,
        ignored=False,
        motivo="Job aceptado",
    )
    assert resp_custom.status == "enqueued"
    assert resp_custom.job_id == 101
    assert resp_custom.motivo == "Job aceptado"


def test_whatsapp_webhook_unauthorized(client):
    """Verifies HTTP 401 when missing or providing invalid X-Webhook-Secret."""
    res = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"event": "messages.upsert", "data": {"remote_jid": "123"}},
        headers={"X-Webhook-Secret": "wrong_secret"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"

    # Missing header altogether
    res_no_header = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"event": "messages.upsert", "data": {"remote_jid": "123"}},
    )
    assert res_no_header.status_code == 401


def test_whatsapp_webhook_invalid_json(client):
    """Verifies HTTP 400 when body is not valid JSON."""
    res = client.post(
        "/api/v1/webhooks/whatsapp",
        data="invalid-not-json",
        content_type="application/json",
        headers={"X-Webhook-Secret": "dev-webhook-secret"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "BAD_REQUEST"


def test_whatsapp_webhook_validation_error_422(client):
    """Verifies HTTP 422 when payload does not conform to schema."""
    res = client.post(
        "/api/v1/webhooks/whatsapp",
        json={"incompleto": True},
        headers={"X-Webhook-Secret": "dev-webhook-secret"},
    )
    assert res.status_code == 422
    assert res.get_json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


def test_whatsapp_webhook_ignores_from_me(client):
    """Verifies that outgoing messages from this instance are ignored without error."""
    payload = {
        "event": "messages.upsert",
        "instance": "gamma",
        "data": {
            "key": {
                "remoteJid": "595981123456@s.whatsapp.net",
                "fromMe": True,
            },
            "message": {
                "conversation": "Respuesta enviada por el bot",
            },
        },
    }
    res = client.post(
        "/api/v1/webhooks/whatsapp",
        json=payload,
        headers={"X-Webhook-Secret": "dev-webhook-secret"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ignored"
    assert data["ignored"] is True
    assert worker.get_pending_count() == 0


def test_whatsapp_webhook_ignores_empty_text(client):
    """Verifies that messages without text content are ignored gracefully."""
    payload = {
        "event": "messages.upsert",
        "instance": "gamma",
        "data": {
            "key": {
                "remoteJid": "595981123456@s.whatsapp.net",
                "fromMe": False,
            },
            "message": {},
        },
    }
    res = client.post(
        "/api/v1/webhooks/whatsapp",
        json=payload,
        headers={"X-Webhook-Secret": "dev-webhook-secret"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ignored"
    assert data["ignored"] is True


def test_whatsapp_webhook_enqueues_successfully(client):
    """Verifies that incoming user message is enqueued into cola.db with channel=whatsapp."""
    payload = {
        "event": "messages.upsert",
        "instance": "gamma",
        "data": {
            "key": {
                "remoteJid": "595981777888@s.whatsapp.net",
                "fromMe": False,
            },
            "pushName": "Kevin Pera",
            "message": {
                "conversation": "Registrar gasto 45000 almuerzo",
            },
        },
    }
    res = client.post(
        "/api/v1/webhooks/whatsapp",
        json=payload,
        headers={"X-Webhook-Secret": "dev-webhook-secret"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "enqueued"
    assert data["ignored"] is False
    assert data["job_id"] is not None
    job_id = data["job_id"]

    # Confirm job is in database
    conn = worker.get_connection()
    try:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (job_id,)).fetchone()
        assert row is not None
        assert row["recipient_id"] == "595981777888@s.whatsapp.net"
        assert row["channel"] == "whatsapp"
        assert row["operacion"] == "procesar_mensaje_whatsapp"
        assert row["estado"] == "pendiente"
    finally:
        conn.close()
