import os
import sys
from unittest.mock import MagicMock, patch
import pytest

os.environ["X_API_KEY"] = "test-secret-key"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)


@pytest.fixture
def client():
    with patch("com.bot.GAMMA") as MockGamma, patch(
        "logic.cron_jobs.notificacion_clima"
    ), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
        mock_instance = MockGamma.return_value
        mock_instance.bot = MagicMock()
        mock_instance.token = "test_token_123"
        from flask_app import app

        app.config["TESTING"] = True
        with app.test_client() as test_client:
            yield test_client


def test_ejecutar_cierre_laboral_datos_reales(client):
    headers = {"X-API-KEY": "test-secret-key"}
    mock_analiticas = {
        "periodo": "Octubre 2026",
        "total_horas_decimal": 142.5,
        "salario_acumulado_gs": 2085345,
    }

    with patch(
        "logic.logic.AgenteAutonomoHoras.calcular_analiticas_asistencia",
        return_value=(mock_analiticas, None),
    ):
        res = client.post(
            "/api/v1/cierres/ejecutar",
            headers=headers,
            json={"tipo": "horas", "hoja": "Octubre 2026"},
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data["total_horas"] == 142.5
    assert data["total_monto"] == 2085345
    assert "cierre_laboral" in data["pdf_url"]


def test_ejecutar_cierre_contable_datos_reales(client):
    headers = {"X-API-KEY": "test-secret-key"}
    mock_balance = {
        "ingresos": 3000000,
        "gastos": 1200000,
        "flujo_neto": 1800000,
        "saldo_acumulado": 2500000,
    }

    with patch(
        "repositories.sheets_repository.SheetsRepository.obtener_balance",
        return_value=mock_balance,
    ):
        res = client.post(
            "/api/v1/cierres/ejecutar",
            headers=headers,
            json={"tipo": "contable", "hoja": "Octubre 2026"},
        )

    assert res.status_code == 200
    data = res.get_json()
    assert data["tipo"] == "contable"
    assert data["total_horas"] == 0.0
    assert data["total_monto"] == 1800000
    assert "cierre_contable" in data["pdf_url"]
