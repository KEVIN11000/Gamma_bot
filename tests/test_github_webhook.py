import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure environment variables
os.environ["TOKEN"] = "test_token_123"
os.environ["CHAT_ID"] = "123456"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"
os.environ["FLASK_ENV"] = "development"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test_webhook_secret_key"

# Ensure src is on sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402
    from services.github_service import GitHubWebhookService  # noqa: E402
    import api.blueprint as blueprint_mod  # noqa: E402


SECRET = "test_webhook_secret_key"


def _generate_signature(payload_bytes: bytes, secret: str = SECRET) -> str:
    mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", SECRET)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_tickets_db(tmp_path, monkeypatch):
    """Fixture que aísla el archivo de tickets en un directorio temporal."""
    test_tickets = [
        {
            "id": "TCK-006",
            "asunto": "Despliegue y recarga de worker en PythonAnywhere",
            "descripcion": "Sincronizar rama Main-stable y recargar servidor WSGI de producción.",
            "estado": "Abierto",
            "fecha": "15/10/2026",
            "origen": "servidor",
            "resolucion": None,
        },
        {
            "id": "TCK-001",
            "asunto": "Configuración de Conexión y API Key",
            "descripcion": "Falta de interfaz para ingresar URL de servidor.",
            "estado": "Cerrado",
            "fecha": "14/10/2026",
            "origen": "app",
            "resolucion": "Implementada tarjeta de Conexión.",
        },
    ]
    temp_tickets_file = tmp_path / "tickets.json"
    with open(temp_tickets_file, "w", encoding="utf-8") as f:
        json.dump(test_tickets, f, indent=2, ensure_ascii=False)

    monkeypatch.setattr(blueprint_mod, "TICKETS_FILE", temp_tickets_file)
    return temp_tickets_file


# ── Tests de Métodos Unitarios en GitHubWebhookService ──────────────────────
def test_extract_ticket_id():
    assert GitHubWebhookService.extract_ticket_id("[TCK-006] Despliegue worker") == "TCK-006"
    assert GitHubWebhookService.extract_ticket_id("Fix [tck-123] algo") == "TCK-123"
    assert GitHubWebhookService.extract_ticket_id("Bug sin etiqueta") is None
    assert GitHubWebhookService.extract_ticket_id(None) is None


def test_verify_signature_unit():
    payload = b'{"hello": "world"}'
    sig = _generate_signature(payload, SECRET)

    assert GitHubWebhookService.verify_signature(payload, sig, SECRET) is True
    assert GitHubWebhookService.verify_signature(payload, "sha256=badbad", SECRET) is False
    assert GitHubWebhookService.verify_signature(payload, None, SECRET) is False
    assert GitHubWebhookService.verify_signature(payload, "invalid_prefix", SECRET) is False
    # Modo permisivo si secret está vacío o no configurado
    assert GitHubWebhookService.verify_signature(payload, None, secret="") is True
    with patch.dict(os.environ, {}, clear=True):
        assert GitHubWebhookService.verify_signature(payload, None) is True


# ── Tests de Integración del Endpoint /webhooks/github ───────────────────────
def test_webhook_ping_event(client):
    payload = b'{"zen": "Design for failure."}'
    sig = _generate_signature(payload)

    res = client.post(
        "/api/v1/webhooks/github",
        data=payload,
        content_type="application/json",
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "pong"
    assert "operational" in data["message"]


def test_webhook_invalid_signature_rejected(client):
    payload = b'{"action": "closed"}'
    res = client.post(
        "/api/v1/webhooks/github",
        data=payload,
        content_type="application/json",
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": "sha256=tampered_signature_12345",
        },
    )
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "INVALID_SIGNATURE"


def test_webhook_issue_closed_updates_ticket(client, mock_tickets_db):
    payload_dict = {
        "action": "closed",
        "issue": {
            "number": 42,
            "title": "[TCK-006] Despliegue y recarga de worker en PythonAnywhere",
            "state": "closed",
            "state_reason": "completed",
        },
        "sender": {"login": "developer-user"},
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = _generate_signature(payload_bytes)

    res = client.post(
        "/api/v1/webhooks/github",
        data=payload_bytes,
        content_type="application/json",
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": sig,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "processed"
    assert data["ticket_id"] == "TCK-006"
    assert data["nuevo_estado"] == "Cerrado"
    assert data["issue_number"] == 42

    # Verificar mutación en base de datos aislada
    with open(mock_tickets_db, "r", encoding="utf-8") as f:
        tickets = json.load(f)
    tck_006 = next(t for t in tickets if t["id"] == "TCK-006")
    assert tck_006["estado"] == "Cerrado"
    assert "GitHub Issue #42" in tck_006["resolucion"]


def test_webhook_issue_reopened_updates_ticket(client, mock_tickets_db):
    payload_dict = {
        "action": "reopened",
        "issue": {
            "number": 1,
            "title": "[TCK-001] Configuración de Conexión y API Key",
            "state": "open",
        },
        "sender": {"login": "developer-user"},
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = _generate_signature(payload_bytes)

    res = client.post(
        "/api/v1/webhooks/github",
        data=payload_bytes,
        content_type="application/json",
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": sig,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "processed"
    assert data["ticket_id"] == "TCK-001"
    assert data["nuevo_estado"] == "Abierto"

    # Verificar mutación en base de datos aislada
    with open(mock_tickets_db, "r", encoding="utf-8") as f:
        tickets = json.load(f)
    tck_001 = next(t for t in tickets if t["id"] == "TCK-001")
    assert tck_001["estado"] == "Abierto"


def test_webhook_issue_without_tck_ignored(client, mock_tickets_db):
    payload_dict = {
        "action": "closed",
        "issue": {
            "number": 99,
            "title": "Refactor general de vistas sin ticket",
            "state": "closed",
        },
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = _generate_signature(payload_bytes)

    res = client.post(
        "/api/v1/webhooks/github",
        data=payload_bytes,
        content_type="application/json",
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": sig,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ignored"
    assert "No TCK identifier" in data["reason"]


def test_webhook_unhandled_event_ignored(client):
    payload_dict = {"action": "created", "comment": {"id": 123}}
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = _generate_signature(payload_bytes)

    res = client.post(
        "/api/v1/webhooks/github",
        data=payload_bytes,
        content_type="application/json",
        headers={
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": sig,
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ignored"
    assert "issue_comment" in data["reason"]
