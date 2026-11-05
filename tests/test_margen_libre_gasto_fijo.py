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
    from logic.financiero import calcular_margen_de_ataque  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


HEADERS = {"X-API-KEY": "test-secret-key"}


def test_pausar_deuda_alterna_es_gasto_fijo_y_libera_margen(client):
    """
    Verifica end-to-end que:
    1. Una deuda activa con cuota 500.000 reduce el margen.
    2. Al pausarla vía PUT /obligaciones/DEUDA-1 con estado='Pausado', Es_Gasto_Fijo pasa a 0.
    3. El margen libre disponible aumenta inmediatamente en 500.000.
    """
    repo = SheetsRepository()
    mock_ws = MagicMock()
    mock_records = [
        {
            "ID_Obligacion": "DEUDA-1",
            "Nombre": "Préstamo Personal",
            "Estado": "Activo",
            "Cuota_Referencia_Gs": 500000,
            "Es_Gasto_Fijo": "1",
        }
    ]

    with patch.object(repo, "_get_sheet", return_value=mock_ws), patch.object(
        repo, "_get_records", return_value=mock_records
    ), patch.object(
        repo, "obtener_presupuesto_base_completo", return_value=(6000000, 2500000)
    ):
        # 1. Margen con deuda activa: 6.000.000 - 2.500.000 - 500.000 = 3.000.000
        with patch("logic.financiero.SheetsRepository", return_value=repo):
            margen_inicial = calcular_margen_de_ataque()
            assert margen_inicial == 3000000

        # 2. Pausar la deuda vía endpoint
        with patch(
            "repositories.sheets_repository.SheetsRepository.get_obligacion_by_id",
            return_value=mock_records[0],
        ), patch(
            "repositories.sheets_repository.SheetsRepository.update_obligacion"
        ) as mock_update:
            res = client.put(
                "/api/v1/obligaciones/DEUDA-1",
                json={"estado": "Pausado"},
                headers=HEADERS,
            )
            assert res.status_code == 200
            dict_actualizado = mock_update.call_args[0][1]
            assert dict_actualizado["Estado"] == "Pausado"
            assert dict_actualizado["Es_Gasto_Fijo"] == 0

        # 3. Simular que la base de datos ahora tiene la deuda pausada
        mock_records[0]["Estado"] = "Pausado"
        mock_records[0]["Es_Gasto_Fijo"] = "0"
        repo.cache.clear()

        # 4. Margen con deuda pausada: 6.000.000 - 2.500.000 - 0 = 3.500.000 (+500.000 liberados)
        with patch("logic.financiero.SheetsRepository", return_value=repo):
            margen_post_pausa = calcular_margen_de_ataque()
            assert margen_post_pausa == 3500000


def test_reactivar_deuda_alterna_es_gasto_fijo_y_reduce_margen():
    """Verifica que reactivar una deuda pausada vuelva a computar su cuota como gasto fijo."""
    repo = SheetsRepository()
    mock_ws = MagicMock()
    mock_records = [
        {
            "ID_Obligacion": "DEUDA-PAUSADA",
            "Nombre": "Tarjeta Crédito",
            "Estado": "Pausado",
            "Cuota_Referencia_Gs": 400000,
            "Es_Gasto_Fijo": "0",
        }
    ]

    with patch.object(repo, "_get_sheet", return_value=mock_ws), patch.object(
        repo, "_get_records", return_value=mock_records
    ), patch.object(
        repo, "obtener_presupuesto_base_completo", return_value=(5000000, 2000000)
    ):
        # 1. Margen inicial sin computar deuda pausada = 3.000.000
        with patch("logic.financiero.SheetsRepository", return_value=repo):
            assert calcular_margen_de_ataque() == 3000000

        # 2. Reactivar estado en repositorio
        repo.update_obligacion_estado("DEUDA-PAUSADA", "Activo")
        # Simular reflejo en records
        mock_records[0]["Estado"] = "Activo"
        mock_records[0]["Es_Gasto_Fijo"] = "1"
        repo.cache.clear()

        # 3. Margen recalculado debe deducir la cuota: 5.000.000 - 2.000.000 - 400.000 = 2.600.000
        with patch("logic.financiero.SheetsRepository", return_value=repo):
            assert calcular_margen_de_ataque() == 2600000


def test_desacoplamiento_gastos_operativos_en_dashboard(client):
    """
    Verifica que ni en /dashboard/summary ni en /bootstrap el margen_libre
    se vea reducido por los gastos operativos del mes.
    """
    mock_balance = {
        "saldo_inicial": 500000,
        "ingresos": 6000000,
        "gastos": 3800000,  # Compras de supermercado, farmacia, etc.
        "flujo_neto": 2200000,
        "saldo_acumulado": 2700000,
        "posicion_iva": 0,
        "es_debito_fiscal": False,
    }

    with patch(
        "logic.financiero.AgenteFinanciero.obtener_balance", return_value=mock_balance
    ), patch("logic.financiero.calcular_margen_de_ataque", return_value=2100000):
        # 1. Dashboard Summary
        res_summary = client.get("/api/v1/dashboard/summary", headers=HEADERS)
        assert res_summary.status_code == 200
        data_summary = res_summary.get_json()
        assert data_summary["saldo_acumulado"] == 2700000
        assert data_summary["gastos"] == 3800000
        assert data_summary["margen_libre"] == 2100000  # Inalterado

        # 2. Bootstrap unificado
        with patch("logic.cron_jobs.obtener_datos_clima", return_value={}):
            res_boot = client.get("/api/v1/bootstrap", headers=HEADERS)
            assert res_boot.status_code == 200
            data_boot = res_boot.get_json()
            rf = data_boot["resumen_financiero"]
            assert rf["saldo_acumulado"] == 2700000
            assert rf["margen_libre"] == 2100000  # Inalterado


def test_simulador_proyectos_ignora_deudas_no_fijas(client):
    """
    Verifica que POST /proyectos/simular compute cuotas_actuales (qd_act)
    únicamente para deudas con Es_Gasto_Fijo=1 y no pausadas.
    """
    mock_deudas = [
        # Fija activa -> debe sumar 400.000
        {
            "ID_Obligacion": "D-FIJA",
            "Monto_Inicial": 4000000,
            "Cuotas": 10,
            "Cuota_Referencia_Gs": 400000,
            "Estado": "Activo",
            "Es_Gasto_Fijo": "1",
        },
        # No fija activa -> no debe sumar
        {
            "ID_Obligacion": "D-NO-FIJA",
            "Monto_Inicial": 3000000,
            "Cuotas": 6,
            "Cuota_Referencia_Gs": 500000,
            "Estado": "Activo",
            "Es_Gasto_Fijo": "0",
        },
        # Pausada -> no debe sumar
        {
            "ID_Obligacion": "D-PAUSADA",
            "Monto_Inicial": 2000000,
            "Cuotas": 5,
            "Cuota_Referencia_Gs": 400000,
            "Estado": "Pausado",
            "Es_Gasto_Fijo": "1",
        },
    ]

    with patch(
        "repositories.sheets_repository.SheetsRepository.obtener_presupuesto_base_completo",
        return_value=(6000000, 2000000),
    ), patch(
        "repositories.sheets_repository.SheetsRepository.get_obligaciones_activas",
        return_value=mock_deudas,
    ), patch(
        "repositories.sheets_repository.SheetsRepository.insert_obligacion"
    ):
        payload = {"concepto": "Curso Especialización", "monto": 1200000, "meses": 6}
        res = client.post("/api/v1/proyectos/simular", json=payload, headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    # Cuotas actuales debe ser exactamente 400.000 (sólo la fija activa)
    assert data["cuotas_actuales"] == 400000
    # Cuota mensual del proyecto: 1.200.000 // 6 = 200.000
    assert data["cuota_mensual"] == 200000
    # MLD post proyecto: 6.000.000 - 2.000.000 - 400.000 - 200.000 = 3.400.000
    assert data["margen_libre_post_proyecto"] == 3400000
