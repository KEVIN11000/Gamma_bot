import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Ensure environment
os.environ["X_API_KEY"] = "test-secret-key"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from logic.financiero import AgenteFinanciero


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


def test_obtener_balance_no_duplica_saldo_inicial():
    """Verifica que flujo_neto sea solo ingresos - gastos y saldo_acumulado incluya saldo_inicial exactamente una vez."""
    mock_libro = MagicMock()
    mock_libro.get_all_values.return_value = [
        [
            "Fecha",
            "Movimiento",
            "Proveedor",
            "Factura",
            "Neto",
            "IVA",
            "Total",
            "Categoria",
        ],
        [
            "01/10/2026",
            "Saldo Inicial / Traspaso",
            "Banco",
            "0",
            "1.431.300",
            "0",
            "1.431.300",
            "Apertura",
        ],
        [
            "05/10/2026",
            "Ingreso",
            "Cliente A",
            "1",
            "500.000",
            "0",
            "500.000",
            "Servicios",
        ],
        [
            "10/10/2026",
            "Gasto",
            "Supermercado",
            "2",
            "200.000",
            "0",
            "200.000",
            "Alimentos",
        ],
    ]

    agente = AgenteFinanciero(spreadsheet_id="dummy_sheet")
    agente._ws = mock_libro

    with patch("repositories.sheets_repository._sheets_cache.get", return_value=None):
        res = agente.obtener_balance()

    assert res["saldo_inicial"] == 1431300
    assert res["ingresos"] == 500000
    assert res["gastos"] == 200000
    # flujo_neto operativo = 500.000 - 200.000 = 300.000
    assert res["flujo_neto"] == 300000
    # saldo_acumulado real = 1.431.300 + 300.000 = 1.731.300 (NO 3.162.600)
    assert res["saldo_acumulado"] == 1731300


def test_obtener_balance_solo_saldo_inicial():
    """Caso empírico del HANDOFF: único asiento de apertura de 1.431.300 Gs."""
    mock_libro = MagicMock()
    mock_libro.get_all_values.return_value = [
        [
            "Fecha",
            "Movimiento",
            "Proveedor",
            "Factura",
            "Neto",
            "IVA",
            "Total",
            "Categoria",
        ],
        [
            "01/10/2026",
            "Saldo Inicial / Traspaso",
            "Banco",
            "0",
            "1.431.300",
            "0",
            "1.431.300",
            "Apertura",
        ],
    ]

    agente = AgenteFinanciero(spreadsheet_id="dummy_sheet")
    agente._ws = mock_libro

    with patch("repositories.sheets_repository._sheets_cache.get", return_value=None):
        res = agente.obtener_balance()

    assert res["saldo_inicial"] == 1431300
    assert res["ingresos"] == 0
    assert res["gastos"] == 0
    assert res["flujo_neto"] == 0
    assert res["saldo_acumulado"] == 1431300


def test_dashboard_summary_saldo_acumulado(client):
    """Verifica que GET /api/v1/dashboard/summary retorne el saldo acumulado exacto sin duplicación."""
    mock_balance = {
        "saldo_inicial": 1431300,
        "ingresos": 500000,
        "gastos": 200000,
        "flujo_neto": 300000,
        "saldo_acumulado": 1731300,
        "posicion_iva": 0,
        "es_debito_fiscal": False,
    }

    with patch(
        "logic.financiero.AgenteFinanciero.obtener_balance", return_value=mock_balance
    ):
        with patch("logic.financiero.calcular_margen_de_ataque", return_value=260000):
            res = client.get(
                "/api/v1/dashboard/summary",
                headers={"X-API-KEY": "test-secret-key"},
            )

    assert res.status_code == 200
    data = res.get_json()
    assert data["saldo_acumulado"] == 1731300
    assert data["flujo_neto"] == 300000
    assert data["saldo_inicial"] == 1431300
