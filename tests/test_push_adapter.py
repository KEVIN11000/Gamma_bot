from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch
import pytest

from adapters.notifications.push_adapter import PushNotificationAdapter
from api.v1.routes_dispositivos import set_push_adapter
from app_queue.worker import create_default_dispatcher, despachar_trabajo

# Set required env vars BEFORE importing flask_app
os.environ.setdefault("TOKEN", "test_token_123")
os.environ.setdefault("CHAT_ID", "123456")
os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Provides a temporary json path for push devices isolation."""
    return tmp_path / "dispositivos_test.json"


@pytest.fixture
def push_adapter(
    tmp_storage: Path,
) -> Generator[PushNotificationAdapter, None, None]:
    """Provides a clean PushNotificationAdapter using isolated tmp storage."""
    adapter = PushNotificationAdapter(storage_path=tmp_storage)
    set_push_adapter(adapter)
    yield adapter
    set_push_adapter(None)


@pytest.fixture
def client(push_adapter: PushNotificationAdapter):
    """Provides a test client for the Flask app with the isolated push adapter."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _get_api_headers() -> dict[str, str]:
    api_key = os.getenv("X_API_KEY") or "test-secret-key"
    return {"X-API-KEY": api_key, "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Unit tests: PushNotificationAdapter Core
# ---------------------------------------------------------------------------


def test_push_adapter_register_device(push_adapter: PushNotificationAdapter) -> None:
    token = "device-token-abc-123456789"
    res = push_adapter.registrar_dispositivo(
        device_token=token, platform="android", alias_usuario="Juan"
    )

    assert res["device_token"] == token
    assert res["platform"] == "android"
    assert res["alias_usuario"] == "Juan"
    assert res["activo"] is True
    assert push_adapter.contar_dispositivos() == 1


def test_push_adapter_register_idempotent(
    push_adapter: PushNotificationAdapter,
) -> None:
    token = "device-token-abc-123456789"
    push_adapter.registrar_dispositivo(
        device_token=token, platform="android", alias_usuario="Juan"
    )
    # Re-register with different platform
    push_adapter.registrar_dispositivo(
        device_token=token, platform="ios", alias_usuario="Juan-iPhone"
    )

    assert push_adapter.contar_dispositivos() == 1
    devices = push_adapter.listar_dispositivos()
    assert devices[0]["platform"] == "ios"
    assert devices[0]["alias_usuario"] == "Juan-iPhone"


def test_push_adapter_deactivate_device(push_adapter: PushNotificationAdapter) -> None:
    token1 = "device-token-1111111111"
    token2 = "device-token-2222222222"
    push_adapter.registrar_dispositivo(token1)
    push_adapter.registrar_dispositivo(token2)
    assert push_adapter.contar_dispositivos() == 2

    desactivado = push_adapter.desregistrar_dispositivo(token1)
    assert desactivado is True
    assert push_adapter.contar_dispositivos(solo_activos=True) == 1
    assert push_adapter.contar_dispositivos(solo_activos=False) == 2


def test_push_adapter_empty_token_raises(push_adapter: PushNotificationAdapter) -> None:
    with pytest.raises(ValueError):
        push_adapter.registrar_dispositivo("   ")


def test_push_adapter_disk_persistence(tmp_storage: Path) -> None:
    # First instance creates and saves
    adapter1 = PushNotificationAdapter(storage_path=tmp_storage)
    adapter1.registrar_dispositivo("token-persisted-12345678", platform="web")

    # Second instance loads from same path
    adapter2 = PushNotificationAdapter(storage_path=tmp_storage)
    assert adapter2.contar_dispositivos() == 1
    devs = adapter2.listar_dispositivos()
    assert devs[0]["device_token"] == "token-persisted-12345678"
    assert devs[0]["platform"] == "web"


def test_push_adapter_send_message_simulated(
    push_adapter: PushNotificationAdapter,
) -> None:
    success = push_adapter.send_message(
        recipient_id="token-single-12345",
        message="¡Alerta de prueba!",
        title="Gamma Test",
        extra_data={"monto": 50000},
    )
    assert success is True
    assert len(push_adapter.sent_notifications) == 1
    record = push_adapter.sent_notifications[0]
    assert record.recipient_id == "token-single-12345"
    assert record.message == "¡Alerta de prueba!"
    assert record.title == "Gamma Test"
    assert record.extra_data["monto"] == 50000


def test_push_adapter_send_message_broadcast(
    push_adapter: PushNotificationAdapter,
) -> None:
    push_adapter.registrar_dispositivo("token-device-a-1234567")
    push_adapter.registrar_dispositivo("token-device-b-1234567")

    success = push_adapter.send_message(
        recipient_id="broadcast",
        message="Mensaje general para todos",
    )
    assert success is True
    assert len(push_adapter.sent_notifications) == 2
    tokens_recibidos = {n.recipient_id for n in push_adapter.sent_notifications}
    assert "token-device-a-1234567" in tokens_recibidos
    assert "token-device-b-1234567" in tokens_recibidos


def test_push_adapter_send_document(push_adapter: PushNotificationAdapter) -> None:
    success = push_adapter.send_document(
        recipient_id="token-doc-123456",
        document_path="/var/reports/reporte_mensual.pdf",
        caption="Aquí está tu reporte",
        visible_file_name="reporte.pdf",
    )
    assert success is True
    assert len(push_adapter.sent_notifications) == 1
    record = push_adapter.sent_notifications[0]
    assert "reporte" in record.message
    assert record.extra_data["document_path"] == "/var/reports/reporte_mensual.pdf"
    assert record.extra_data["filename"] == "reporte.pdf"


def test_push_adapter_with_http_client(tmp_storage: Path) -> None:
    mock_http = MagicMock()
    adapter = PushNotificationAdapter(storage_path=tmp_storage, http_client=mock_http)
    adapter.send_message(
        recipient_id="token-http-123456",
        message="Notificación FCM real",
        title="Aviso",
    )
    mock_http.post.assert_called_once()
    call_args = mock_http.post.call_args
    assert "fcm.googleapis.com" in call_args[0][0]
    assert call_args[1]["json"]["to"] == "token-http-123456"


# ---------------------------------------------------------------------------
# REST API tests: routes_dispositivos
# ---------------------------------------------------------------------------


def test_api_registrar_dispositivo_success(
    client, push_adapter: PushNotificationAdapter
) -> None:
    payload = {
        "device_token": "fcm-registration-token-987654321",
        "platform": "android",
        "alias_usuario": "Kevin",
    }
    response = client.post(
        "/api/v1/dispositivos/registrar",
        json=payload,
        headers=_get_api_headers(),
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["registrado"] is True
    assert data["dispositivos_activos"] == 1


def test_api_registrar_dispositivo_missing_auth(client) -> None:
    payload = {"device_token": "fcm-registration-token-987654321"}
    response = client.post("/api/v1/dispositivos/registrar", json=payload)
    assert response.status_code == 401


def test_api_registrar_dispositivo_invalid_payload(client) -> None:
    # Token too short (< 10 chars)
    payload = {"device_token": "short", "platform": "android"}
    response = client.post(
        "/api/v1/dispositivos/registrar",
        json=payload,
        headers=_get_api_headers(),
    )
    assert response.status_code == 422


def test_api_listar_dispositivos(client, push_adapter: PushNotificationAdapter) -> None:
    push_adapter.registrar_dispositivo("token-dispositivo-xyz-12345")
    response = client.get("/api/v1/dispositivos", headers=_get_api_headers())
    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
    assert len(data["dispositivos"]) == 1


def test_api_notificar_dispositivos(
    client, push_adapter: PushNotificationAdapter
) -> None:
    push_adapter.registrar_dispositivo("token-dispositivo-xyz-12345")
    payload = {
        "mensaje": "¡Gastaste el 85% de tu presupuesto de Combustible!",
        "titulo": "Presupuesto Crítico",
    }
    response = client.post(
        "/api/v1/dispositivos/notificar",
        json=payload,
        headers=_get_api_headers(),
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["enviado"] is True


# ---------------------------------------------------------------------------
# Worker & Dispatcher integration tests
# ---------------------------------------------------------------------------


def test_create_default_dispatcher_has_push_channel() -> None:
    dispatcher = create_default_dispatcher()
    assert dispatcher.has_channel("push") is True
    adapter = dispatcher.get_adapter("push")
    assert isinstance(adapter, PushNotificationAdapter)


def test_despachar_trabajo_enviar_notificacion(
    push_adapter: PushNotificationAdapter,
) -> None:
    payload = {
        "mensaje": "Alerta: límite superado",
        "titulo": "Aviso Finanzas",
    }
    despachar_trabajo(
        bot_or_notifier=push_adapter,
        operacion="enviar_notificacion",
        payload=payload,
        recipient_id="token-dest-12345678",
    )
    assert len(push_adapter.sent_notifications) == 1
    rec = push_adapter.sent_notifications[0]
    assert rec.recipient_id == "token-dest-12345678"
    assert rec.message == "Alerta: límite superado"
    assert rec.title == "Aviso Finanzas"
