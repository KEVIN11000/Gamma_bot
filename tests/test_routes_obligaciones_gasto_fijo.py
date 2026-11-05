import os
import sys
from unittest.mock import MagicMock, patch
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
    from repositories.sheets_repository import SheetsRepository  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


HEADERS = {"X-API-KEY": "test-secret-key"}


def test_create_obligacion_con_gasto_fijo_explicit(client):
    payload = {
        "nombre": "Préstamo Personal",
        "monto_inicial": 10000000,
        "cuota_referencia_gs": 1000000,
        "es_gasto_fijo": False,
    }

    with patch("logic.financiero.alta_obligacion") as mock_alta:
        mock_alta.return_value = {
            "ID_Obligacion": "OBL-123456",
            "Nombre": "Préstamo Personal",
            "Es_Gasto_Fijo": 0,
            "Estado": "Activo",
        }
        res = client.post("/api/v1/obligaciones", json=payload, headers=HEADERS)

    assert res.status_code == 201
    mock_alta.assert_called_once()
    assert mock_alta.call_args[1]["es_gasto_fijo"] is False


def test_update_obligacion_pausar_alterna_gasto_fijo(client):
    """Verifica que cambiar el estado a 'Pausado' desactive automáticamente Es_Gasto_Fijo a 0."""
    existente = {
        "ID_Obligacion": "OBL-001",
        "Nombre": "Crédito Auto",
        "Estado": "Activo",
        "Es_Gasto_Fijo": "1",
    }

    with patch.object(
        SheetsRepository, "get_obligacion_by_id", return_value=existente
    ), patch.object(SheetsRepository, "update_obligacion") as mock_update:
        res = client.put(
            "/api/v1/obligaciones/OBL-001",
            json={"estado": "Pausado"},
            headers=HEADERS,
        )

    assert res.status_code == 200
    mock_update.assert_called_once()
    passed_dict = mock_update.call_args[0][1]
    assert passed_dict["Estado"] == "Pausado"
    assert passed_dict["Es_Gasto_Fijo"] == 0


def test_update_obligacion_reactivar_alterna_gasto_fijo(client):
    """Verifica que cambiar el estado a 'Activo' reactive automáticamente Es_Gasto_Fijo a 1."""
    existente = {
        "ID_Obligacion": "OBL-001",
        "Nombre": "Crédito Auto",
        "Estado": "Pausado",
        "Es_Gasto_Fijo": "0",
    }

    with patch.object(
        SheetsRepository, "get_obligacion_by_id", return_value=existente
    ), patch.object(SheetsRepository, "update_obligacion") as mock_update:
        res = client.put(
            "/api/v1/obligaciones/OBL-001",
            json={"estado": "Activo"},
            headers=HEADERS,
        )

    assert res.status_code == 200
    mock_update.assert_called_once()
    passed_dict = mock_update.call_args[0][1]
    assert passed_dict["Estado"] == "Activo"
    assert passed_dict["Es_Gasto_Fijo"] == 1


def test_update_obligacion_estado_sheets_repo_unit():
    """Prueba unitaria en SheetsRepository.update_obligacion_estado con alternancia de celda."""
    repo = SheetsRepository()
    mock_ws = MagicMock()
    mock_records = [
        {"ID_Obligacion": "OBL-UNIT", "Estado": "Activo", "Es_Gasto_Fijo": "1"}
    ]

    with patch.object(repo, "_get_sheet", return_value=mock_ws), patch.object(
        repo, "_get_records", return_value=mock_records
    ):
        repo.update_obligacion_estado("OBL-UNIT", "Pausado")

    # Debe actualizar Estado (columna 2) y Es_Gasto_Fijo (columna 3) a 0
    calls = mock_ws.update_cell.call_args_list
    assert len(calls) == 2
    # El segundo call actualiza Es_Gasto_Fijo a 0
    assert calls[1][0][2] == 0
