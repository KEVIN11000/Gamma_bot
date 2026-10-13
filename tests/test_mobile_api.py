import os
import sys
from unittest.mock import patch, MagicMock
import pytest

# Set required env vars BEFORE importing flask_app
os.environ["TOKEN"] = "test_token_123"
os.environ["CHAT_ID"] = "123456"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"
os.environ["FLASK_ENV"] = "development"
os.environ["CRON_SECRET"] = "test_cron_secret"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["X_API_KEY"] = "test-secret-key"

# Ensure src is on the path
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


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_unauthorized_access(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_health_with_key(client):
    res = client.get("/api/v1/health", headers={"X-API-KEY": "test-secret-key"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["version_api"] == "1.0.0"
    assert "latest_app_version" in data
    assert "download_url" in data


def test_dashboard_summary(client):
    res = client.get(
        "/api/v1/dashboard/summary", headers={"X-API-KEY": "test-secret-key"}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "mes" in data
    assert "flujo_neto" in data
    assert "margen_libre" in data


def test_movimientos_crud(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # GET
    res = client.get("/api/v1/movimientos", headers=headers)
    assert res.status_code == 200

    # POST (IVA 10%)
    payload = {
        "proveedor_cliente": "Supermercado Test",
        "total": 110000,
        "categoria": "Supermercado",
        "tasa_iva": "10%",
        "movimiento": "Gasto",
        "comprobante": "Física Legal",
    }
    res_post = client.post("/api/v1/movimientos", headers=headers, json=payload)
    assert res_post.status_code == 200
    data = res_post.get_json()
    assert data["total"] == 110000
    assert data["iva"] == 10000
    assert data["neto"] == 100000


def test_obligaciones_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # GET
    res = client.get("/api/v1/obligaciones", headers=headers)
    assert res.status_code == 200

    # POST create
    res_create = client.post(
        "/api/v1/obligaciones",
        headers=headers,
        json={"nombre": "Préstamo Auto", "monto_inicial": 5000000, "tipo": "Deuda"},
    )
    assert res_create.status_code == 201
    ob_id = res_create.get_json()["ID_Obligacion"]

    # Simular
    res_sim = client.post(
        "/api/v1/obligaciones/simular",
        headers=headers,
        json={"monto": 12000000, "meses": 12},
    )
    assert res_sim.status_code == 200
    assert "cuota_mensual" in res_sim.get_json()

    # Abonar
    res_abono = client.post(
        "/api/v1/obligaciones/abonar",
        headers=headers,
        json={"id_obligacion": ob_id, "monto": 1000000},
    )
    assert res_abono.status_code == 200


def test_avisos_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # POST
    res_post = client.post(
        "/api/v1/avisos",
        headers=headers,
        json={
            "titulo": "Test Aviso",
            "fecha_evento": "20/10/2026 14:00",
            "dias_restantes": 7,
        },
    )
    assert res_post.status_code == 201
    aviso_id = res_post.get_json()["id"]

    # GET
    res_get = client.get("/api/v1/avisos", headers=headers)
    assert res_get.status_code == 200

    # DELETE
    res_del = client.delete(f"/api/v1/avisos/{aviso_id}", headers=headers)
    assert res_del.status_code == 200


def test_asistencia_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}
    res_marcar = client.post(
        "/api/v1/asistencia/marcar", headers=headers, json={"modo": "normal"}
    )
    assert res_marcar.status_code == 200
    assert "Marcación laboral exitosa" in res_marcar.get_json()["mensaje"]

    res_materia = client.post(
        "/api/v1/asistencia/materia", headers=headers, json={"materia": "Mecatrónica"}
    )
    assert res_materia.status_code == 200
    assert "Mecatrónica" in res_materia.get_json()["mensaje"]


def test_cierres_and_pdf(client):
    headers = {"X-API-KEY": "test-secret-key"}
    res_cierre = client.post(
        "/api/v1/cierres/ejecutar", headers=headers, json={"hoja": "Octubre 2026"}
    )
    assert res_cierre.status_code == 200
    pdf_url = res_cierre.get_json()["pdf_url"]

    # Descarga estática
    filename = pdf_url.split("/")[-1]
    res_pdf = client.get(f"/api/v1/cierres/reportes/{filename}")
    assert res_pdf.status_code == 200
    assert res_pdf.content_type == "application/pdf"


def test_soporte_tickets_and_logs(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # Ticket POST
    res_post = client.post(
        "/api/v1/soporte/tickets",
        headers=headers,
        json={"asunto": "Fallo sincronización", "descripcion": "Prueba unitaria"},
    )
    assert res_post.status_code == 201

    # Ticket GET
    res_get = client.get("/api/v1/soporte/tickets", headers=headers)
    assert res_get.status_code == 200

    # Logs
    res_logs = client.get("/api/v1/sistema/logs", headers=headers)
    assert res_logs.status_code == 200
    assert len(res_logs.get_json()) >= 1
