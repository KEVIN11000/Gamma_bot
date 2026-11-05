import os
import sys
from unittest.mock import patch, MagicMock
import pytest

os.environ["TOKEN"] = "test_token_123"
os.environ["CHAT_ID"] = "123456"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"
os.environ["FLASK_ENV"] = "development"
os.environ["CRON_SECRET"] = "test_cron_secret"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["X_API_KEY"] = "test-secret-key"

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


HEADERS = {"X-API-KEY": "test-secret-key"}


def test_simular_proyecto_unauthorized(client):
    res = client.post("/api/v1/proyectos/simular", json={"monto": 1000000, "meses": 12})
    assert res.status_code == 401


def test_simular_proyecto_validation_error(client):
    res = client.post(
        "/api/v1/proyectos/simular",
        headers=HEADERS,
        json={"concepto": "", "monto": -100, "meses": 0},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "VALIDATION_ERROR"


@patch("repositories.sheets_repository.SheetsRepository.insert_obligacion")
@patch("repositories.sheets_repository.SheetsRepository.get_obligaciones_activas")
@patch(
    "repositories.sheets_repository.SheetsRepository.obtener_presupuesto_base_completo"
)
def test_simular_proyecto_viable(mock_base, mock_debts, mock_insert, client):
    mock_base.return_value = (10000000, 2000000)  # Ingreso: 10M, GF: 2M
    mock_debts.return_value = [
        {"Monto_Inicial": 6000000, "Cuotas": 12}  # Cuota actual: 500k
    ]

    # Nueva cuota: 3.6M / 12 = 300k. Total cuotas = 800k. DTI = 800k/10M = 8% <= 30% -> Viable
    res = client.post(
        "/api/v1/proyectos/simular",
        headers=HEADERS,
        json={"concepto": "Notebook Profesional", "monto": 3600000, "meses": 12},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["id_proyecto"].startswith("PRY-")
    assert data["concepto"] == "Notebook Profesional"
    assert data["monto_total"] == 3600000
    assert data["meses"] == 12
    assert data["cuota_mensual"] == 300000
    assert data["ingreso_base"] == 10000000
    assert data["gastos_fijos"] == 2000000
    assert data["cuotas_actuales"] == 500000
    assert (
        data["margen_libre_post_proyecto"] == 10000000 - 2000000 - 500000 - 300000
    )  # 7.2M
    assert data["dti_resultante"] == 8.0
    assert data["diagnostico"] == "Viable"
    assert data["semaforo"] == "VERDE"

    mock_insert.assert_called_once()
    saved = mock_insert.call_args[0][0]
    assert saved["Estado"] == "Simulado"
    assert saved["Tipo"] == "Proyecto"


@patch("repositories.sheets_repository.SheetsRepository.insert_obligacion")
@patch("repositories.sheets_repository.SheetsRepository.get_obligaciones_activas")
@patch(
    "repositories.sheets_repository.SheetsRepository.obtener_presupuesto_base_completo"
)
def test_simular_proyecto_ajustado(mock_base, mock_debts, mock_insert, client):
    mock_base.return_value = (5000000, 1000000)  # Ingreso: 5M, GF: 1M
    mock_debts.return_value = [{"Monto_Inicial": 12000000, "Cuotas": 12}]  # Cuota: 1M

    # Nueva cuota: 8.4M / 12 = 700k. Total cuotas = 1.7M. DTI = 1.7M / 5M = 34.0% -> Ajustado (31-40%)
    res = client.post(
        "/api/v1/proyectos/simular",
        headers=HEADERS,
        json={"concepto": "Moto Nueva", "monto": 8400000, "meses": 12},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["dti_resultante"] == 34.0
    assert data["diagnostico"] == "Ajustado"
    assert data["semaforo"] == "AMARILLO"


@patch("repositories.sheets_repository.SheetsRepository.insert_obligacion")
@patch("repositories.sheets_repository.SheetsRepository.get_obligaciones_activas")
@patch(
    "repositories.sheets_repository.SheetsRepository.obtener_presupuesto_base_completo"
)
def test_simular_proyecto_riesgo(mock_base, mock_debts, mock_insert, client):
    mock_base.return_value = (4000000, 2000000)  # Ingreso: 4M, GF: 2M
    mock_debts.return_value = [{"Monto_Inicial": 12000000, "Cuotas": 12}]  # Cuota: 1M

    # Nueva cuota: 12M / 12 = 1M. Total cuotas = 2M. DTI = 2M / 4M = 50.0% -> Riesgo (>40%)
    res = client.post(
        "/api/v1/proyectos/simular",
        headers=HEADERS,
        json={"concepto": "Refacción Mayor", "monto": 12000000, "meses": 12},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["dti_resultante"] == 50.0
    assert data["diagnostico"] == "Riesgo"
    assert data["semaforo"] == "ROJO"


def test_aprobar_proyecto_unauthorized(client):
    res = client.post("/api/v1/proyectos/PRY-1234/aprobar")
    assert res.status_code == 401


@patch("repositories.sheets_repository.SheetsRepository.get_obligacion_by_id")
def test_aprobar_proyecto_not_found(mock_get, client):
    mock_get.return_value = {}
    res = client.post("/api/v1/proyectos/PRY-NOEXISTE/aprobar", headers=HEADERS)
    assert res.status_code == 404
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "NOT_FOUND"


@patch("repositories.sheets_repository.SheetsRepository.update_obligacion_estado")
@patch("repositories.sheets_repository.SheetsRepository.get_obligacion_by_id")
def test_aprobar_proyecto_success(mock_get, mock_update, client):
    mock_get.return_value = {
        "ID_Obligacion": "PRY-A1B2C3",
        "Nombre": "Notebook",
        "Estado": "Simulado",
    }

    res = client.post("/api/v1/proyectos/PRY-A1B2C3/aprobar", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["id_proyecto"] == "PRY-A1B2C3"
    assert data["estado"] == "Activo"
    mock_update.assert_called_once_with("PRY-A1B2C3", "Activo")


@patch("repositories.sheets_repository.SheetsRepository.update_obligacion_estado")
@patch("repositories.sheets_repository.SheetsRepository.get_obligacion_by_id")
def test_aprobar_proyecto_already_active(mock_get, mock_update, client):
    mock_get.return_value = {
        "ID_Obligacion": "PRY-A1B2C3",
        "Nombre": "Notebook",
        "Estado": "Activo",
    }

    res = client.post("/api/v1/proyectos/PRY-A1B2C3/aprobar", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["mensaje"] == "El proyecto ya se encontraba activo."
    mock_update.assert_not_called()
