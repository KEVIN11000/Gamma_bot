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


def test_presupuesto_fijos_unauthorized(client):
    res = client.get("/api/v1/presupuesto/fijos")
    assert res.status_code == 401


@patch(
    "repositories.sheets_repository.SheetsRepository.obtener_presupuesto_base_completo"
)
@patch("repositories.sheets_repository.SheetsRepository.obtener_gastos_fijos")
def test_get_gastos_fijos_success(mock_gf, mock_pbc, client):
    mock_pbc.return_value = (6500000, 2500000)
    mock_gf.return_value = {
        "total": 2500000,
        "gastos": {
            "Vivienda": [
                {"concepto": "Alquiler", "monto": 1500000, "fila": 2},
                {"concepto": "Expensas", "monto": 250000, "fila": 3},
            ],
            "Servicios": [
                {"concepto": "Internet", "monto": 180000, "fila": 4},
            ],
        },
    }

    res = client.get("/api/v1/presupuesto/fijos", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["salario_base"] == 6500000
    assert data["total_gastos_fijos"] == 2500000
    assert "Vivienda" in data["categorias"]
    assert len(data["categorias"]["Vivienda"]) == 2
    assert data["categorias"]["Vivienda"][0]["concepto"] == "Alquiler"
    assert data["categorias"]["Vivienda"][0]["monto"] == 1500000


@patch(
    "repositories.sheets_repository.SheetsRepository.obtener_presupuesto_base_completo"
)
def test_get_gastos_fijos_error(mock_pbc, client):
    mock_pbc.side_effect = RuntimeError("Conexión perdida con Google Sheets")
    res = client.get("/api/v1/presupuesto/fijos", headers=HEADERS)
    assert res.status_code == 500
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "SHEETS_ERROR"


def test_update_gasto_fijo_validation(client):
    # Invalid body
    res = client.put(
        "/api/v1/presupuesto/fijos/Alquiler",
        headers=HEADERS,
        json={"nuevo_monto": -100},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "VALIDATION_ERROR"


@patch("repositories.sheets_repository.SheetsRepository.actualizar_monto_gasto_fijo")
def test_update_gasto_fijo_not_found(mock_update, client):
    mock_update.return_value = False
    res = client.put(
        "/api/v1/presupuesto/fijos/ConceptoFantasma",
        headers=HEADERS,
        json={"nuevo_monto": 500000},
    )
    assert res.status_code == 404
    data = res.get_json()
    assert data["code"] == "NOT_FOUND"


@patch("repositories.sheets_repository.SheetsRepository.actualizar_monto_gasto_fijo")
def test_update_gasto_fijo_success(mock_update, client):
    mock_update.return_value = True
    res = client.put(
        "/api/v1/presupuesto/fijos/Alquiler",
        headers=HEADERS,
        json={"nuevo_monto": 1700000},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["concepto"] == "Alquiler"
    assert data["nuevo_monto"] == 1700000
    mock_update.assert_called_once_with(concepto_id="Alquiler", nuevo_monto=1700000)


def test_add_gasto_fijo_validation(client):
    res = client.post(
        "/api/v1/presupuesto/fijos",
        headers=HEADERS,
        json={"categoria": "", "concepto": "", "monto": 0},
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["code"] == "VALIDATION_ERROR"


@patch("repositories.sheets_repository.SheetsRepository.agregar_gasto_fijo")
def test_add_gasto_fijo_success(mock_add, client):
    mock_add.return_value = True
    res = client.post(
        "/api/v1/presupuesto/fijos",
        headers=HEADERS,
        json={
            "categoria": "Suscripciones",
            "concepto": "Spotify Familiar",
            "monto": 65000,
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["concepto"] == "Spotify Familiar"
    assert data["categoria"] == "Suscripciones"
    assert data["monto"] == 65000


@patch(
    "repositories.sheets_repository.SheetsRepository.upsert_salario_presupuesto_base"
)
def test_update_salario_base(mock_upsert, client):
    # Validation error
    res_bad = client.put(
        "/api/v1/presupuesto/salario-base",
        headers=HEADERS,
        json={"nuevo_salario": 0},
    )
    assert res_bad.status_code == 400

    # Success
    mock_upsert.return_value = True
    res_ok = client.put(
        "/api/v1/presupuesto/salario-base",
        headers=HEADERS,
        json={"nuevo_salario": 7500000},
    )
    assert res_ok.status_code == 200
    data = res_ok.get_json()
    assert data["status"] == "ok"
    assert data["nuevo_salario"] == 7500000


@patch("logic.financiero.evaluar_techo_presupuestario")
@patch("repositories.sheets_repository.SheetsRepository._get_sheet")
@patch("repositories.sheets_repository.SheetsRepository._get_records")
def test_get_techos_presupuestarios(mock_records, mock_sheet, mock_eval, client):
    mock_sheet.return_value = MagicMock()
    mock_records.return_value = [
        {"Categoria": "Supermercado", "Monto_Mensual_Gs": "1200000"},
        {"Categoria": "Combustible", "Monto_Mensual_Gs": "600000"},
    ]

    def fake_eval(categoria, monto_nuevo=0.0, sheets_repo=None, local_repo=None):
        if categoria == "Supermercado":
            return {
                "categoria": "Supermercado",
                "limite_presupuesto": 1200000,
                "monto_gastado": 1000000,
                "porcentaje_consumido": 83.3,
                "umbral_configurado": 80,
                "alerta_emitida": True,
                "mensaje": "Has consumido el 83.3%",
            }
        elif categoria == "Combustible":
            return {
                "categoria": "Combustible",
                "limite_presupuesto": 600000,
                "monto_gastado": 250000,
                "porcentaje_consumido": 41.6,
                "umbral_configurado": 80,
                "alerta_emitida": False,
                "mensaje": "Dentro del límite",
            }
        return {"limite_presupuesto": 0}

    mock_eval.side_effect = fake_eval

    res = client.get("/api/v1/presupuesto/techos", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data) == 2

    # Verify Supermercado
    superm = next(item for item in data if item["categoria"] == "Supermercado")
    assert superm["limite_mensual"] == 1200000
    assert superm["consumido"] == 1000000
    assert superm["porcentaje"] == 83.3
    assert superm["alerta_emitida"] is True
    assert superm["estado"] == "ALERTA"

    # Verify Combustible
    comb = next(item for item in data if item["categoria"] == "Combustible")
    assert comb["limite_mensual"] == 600000
    assert comb["consumido"] == 250000
    assert comb["porcentaje"] == 41.6
    assert comb["alerta_emitida"] is False
    assert comb["estado"] == "NORMAL"
