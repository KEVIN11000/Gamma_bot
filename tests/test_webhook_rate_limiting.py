from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from api.security import limiter, get_client_ip

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
def reset_limits():
    """Limpia el rate limiter antes y después de cada test."""
    limiter.reset()
    yield
    limiter.reset()


class TestWebhookRateLimiting:
    """Verifica limitación de tasa y hardening en POST /api/v1/webhooks/whatsapp."""

    def test_get_client_ip_forwarded(self, client):
        """Verifica que get_client_ip priorice X-Forwarded-For."""
        with app.test_request_context(
            "/api/v1/webhooks/whatsapp",
            headers={"X-Forwarded-For": "203.0.113.195, 10.0.0.1"},
        ):
            ip = get_client_ip()
            assert ip == "203.0.113.195"

    def test_get_client_ip_fallback(self, client):
        """Verifica que get_client_ip use remote_addr cuando no hay proxy."""
        with app.test_request_context(
            "/api/v1/webhooks/whatsapp", environ_base={"REMOTE_ADDR": "192.168.1.50"}
        ):
            ip = get_client_ip()
            assert ip == "192.168.1.50"

    @patch("api.v1.routes_webhooks.enqueue")
    def test_webhook_burst_triggers_429(self, mock_enqueue, client):
        """Envía ráfaga de peticiones y verifica que tras 60 requests retorne 429."""
        mock_enqueue.return_value = 101

        valid_payload = {
            "event": "messages.upsert",
            "instance": "gamma",
            "data": {
                "key": {"remoteJid": "595981123456@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Hola bot"},
            },
        }
        headers = {
            "X-Webhook-Secret": "dev-webhook-secret",
            "X-Forwarded-For": "203.0.113.1",
        }

        # Enviar 60 peticiones válidas permitidas
        for _ in range(60):
            resp = client.post(
                "/api/v1/webhooks/whatsapp",
                headers=headers,
                json=valid_payload,
            )
            assert resp.status_code == 200

        # La petición 61 debe ser rechazada con 429
        resp_blocked = client.post(
            "/api/v1/webhooks/whatsapp",
            headers=headers,
            json=valid_payload,
        )
        assert resp_blocked.status_code == 429
        data = resp_blocked.get_json()
        assert data["error"]["code"] == "TOO_MANY_REQUESTS"
        # mock_enqueue no debió ser llamado en la petición bloqueada (se mantiene en 60)
        assert mock_enqueue.call_count == 60

    @patch("api.v1.routes_webhooks.enqueue")
    def test_webhook_independent_ip_limits(self, mock_enqueue, client):
        """Verifica que el límite se aísla por IP del cliente."""
        mock_enqueue.return_value = 102
        valid_payload = {
            "event": "messages.upsert",
            "instance": "gamma",
            "data": {
                "key": {"remoteJid": "595981123456@s.whatsapp.net", "fromMe": False},
                "message": {"conversation": "Mensaje"},
            },
        }

        # IP A agota su cuota de 60
        for _ in range(60):
            client.post(
                "/api/v1/webhooks/whatsapp",
                headers={
                    "X-Webhook-Secret": "dev-webhook-secret",
                    "X-Forwarded-For": "198.51.100.5",
                },
                json=valid_payload,
            )

        resp_a = client.post(
            "/api/v1/webhooks/whatsapp",
            headers={
                "X-Webhook-Secret": "dev-webhook-secret",
                "X-Forwarded-For": "198.51.100.5",
            },
            json=valid_payload,
        )
        assert resp_a.status_code == 429

        # IP B debe poder realizar peticiones con normalidad
        resp_b = client.post(
            "/api/v1/webhooks/whatsapp",
            headers={
                "X-Webhook-Secret": "dev-webhook-secret",
                "X-Forwarded-For": "198.51.100.6",
            },
            json=valid_payload,
        )
        assert resp_b.status_code == 200

    def test_webhook_payload_too_large(self, client):
        """Verifica que peticiones con cuerpo excesivo (>64KB) retornen 413."""
        resp = client.post(
            "/api/v1/webhooks/whatsapp",
            headers={
                "X-Webhook-Secret": "dev-webhook-secret",
                "Content-Length": "70000",
            },
            data="A" * 70000,
        )
        assert resp.status_code == 413
        data = resp.get_json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
