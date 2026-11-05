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
    from logic.financiero import calcular_margen_de_ataque  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


HEADERS = {"X-API-KEY": "test-secret-key"}


def test_calcular_margen_de_ataque_solo_deudas_fijas():
    """
    Verifica que:
    1. Se compute sólo deudas con Es_Gasto_Fijo=1 y no pausadas.
    2. Deudas con Es_Gasto_Fijo=0 se ignoren.
    3. Deudas pausadas se ignoren aunque tengan Es_Gasto_Fijo=1.
    """
    mock_repo = MagicMock()
    # Ingresos base: 6.500.000, Gastos fijos: 2.850.000
    mock_repo.obtener_presupuesto_base_completo.return_value = (6500000, 2850000)

    mock_repo.get_obligaciones_activas.return_value = [
        # Deuda fija activa (debe restar 500.000)
        {
            "ID_Obligacion": "D1",
            "Estado": "Activo",
            "Cuota_Referencia_Gs": 500000,
            "Es_Gasto_Fijo": "1",
        },
        # Deuda no fija (ej. préstamo ocasional sin cuota estructural fija, no debe restar)
        {
            "ID_Obligacion": "D2",
            "Estado": "Activo",
            "Cuota_Referencia_Gs": 300000,
            "Es_Gasto_Fijo": "0",
        },
        # Deuda pausada (no debe restar aunque tenga Es_Gasto_Fijo=1)
        {
            "ID_Obligacion": "D3",
            "Estado": "Pausado",
            "Cuota_Referencia_Gs": 200000,
            "Es_Gasto_Fijo": "1",
        },
    ]

    with patch("logic.financiero.SheetsRepository", return_value=mock_repo):
        margen = calcular_margen_de_ataque()

    # 6.500.000 - 2.850.000 - 500.000 = 3.150.000
    assert margen == 3150000


def test_calcular_margen_de_ataque_compatibilidad_legacy():
    """Verifica compatibilidad con registros antiguos que no tengan el campo Es_Gasto_Fijo."""
    mock_repo = MagicMock()
    mock_repo.obtener_presupuesto_base_completo.return_value = (5000000, 2000000)
    mock_repo.get_obligaciones_activas.return_value = [
        {
            "ID_Obligacion": "LEGACY-1",
            "Estado": "Activo",
            "Cuota_Referencia_Gs": 400000,
            # Sin clave Es_Gasto_Fijo
        }
    ]

    with patch("logic.financiero.SheetsRepository", return_value=mock_repo):
        margen = calcular_margen_de_ataque()

    # 5.000.000 - 2.000.000 - 400.000 = 2.600.000
    assert margen == 2600000


def test_dashboard_summary_margen_desacoplado_de_gastos_operativos(client):
    """
    Verifica que en /dashboard/summary el margen libre no sea contaminado
    por los gastos operativos diarios del mes.
    """
    mock_balance = {
        "saldo_inicial": 1000000,
        "ingresos": 6500000,
        "gastos": 4200000,  # Gastos operativos altos en Libro Diario
        "flujo_neto": 2300000,
        "saldo_acumulado": 3300000,
        "posicion_iva": 0,
        "es_debito_fiscal": False,
    }

    with patch(
        "logic.financiero.AgenteFinanciero.obtener_balance", return_value=mock_balance
    ), patch("logic.financiero.calcular_margen_de_ataque", return_value=2550000):
        res = client.get("/api/v1/dashboard/summary", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    # El saldo acumulado refleja los gastos reales (1.000.000 + 6.500.000 - 4.200.000 = 3.300.000)
    assert data["saldo_acumulado"] == 3300000
    assert data["gastos"] == 4200000
    # El margen libre permanece en 2.550.000 constante e inalterado por los 4.200.000 de gastos
    assert data["margen_libre"] == 2550000
