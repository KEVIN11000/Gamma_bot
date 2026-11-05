import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock
import pytest
import pytz

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
    from api.schemas import EstadoJornadaHoyResponse  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


HEADERS = {"X-API-KEY": "test-secret-key"}
tz_py = pytz.timezone("America/Asuncion")


def test_bootstrap_unauthorized(client):
    res = client.get("/api/v1/bootstrap")
    assert res.status_code == 401


def test_bootstrap_success_completo(client):
    mock_balance = {
        "saldo_inicial": 1000000,
        "ingresos": 5000000,
        "gastos": 2500000,
        "flujo_neto": 2500000,
        "saldo_acumulado": 3500000,
        "posicion_iva": 150000,
        "es_debito_fiscal": False,
    }
    mock_estado = EstadoJornadaHoyResponse(
        fecha="04/11/2026",
        estado="TRABAJANDO",
        hora_entrada="08:00",
        hora_salida=None,
        minutos_transcurridos=120,
        tiempo_transcurrido_formato="2h 00m",
        puede_marcar_entrada=False,
        puede_marcar_salida=True,
        es_feriado_o_descanso=False,
    )
    mock_clima = {
        "temperatura_actual": 25.5,
        "temperatura_min": 20.0,
        "temperatura_max": 28.0,
        "condicion": "Lluvia ligera",
        "alerta_paraguas": {
            "necesita_paraguas": True,
            "probabilidad_lluvia": 80,
            "motivo": "Llevar paraguas",
        },
        "actualizado_at": "2026-11-04T10:00:00",
    }
    mock_avisos = [
        {"id": "av-1", "titulo": "Renovar seguro", "fecha_evento": "05/11/2026 09:00"}
    ]
    mock_vencimientos = {
        "mes_actual": 11,
        "dia_actual": 4,
        "vencimientos": [
            {
                "id": "DEUDA-001",
                "nombre": "Préstamo Banco",
                "dia_vencimiento": 10,
                "cuota": 650000,
                "saldo": 7550000,
                "vencida": False,
            }
        ],
    }

    with patch(
        "logic.financiero.AgenteFinanciero.obtener_balance", return_value=mock_balance
    ), patch("logic.financiero.calcular_margen_de_ataque", return_value=1850000), patch(
        "api.v1.routes_asistencia.obtener_estado_jornada_hoy_dto",
        return_value=mock_estado,
    ), patch(
        "logic.cron_jobs.obtener_datos_clima", return_value=mock_clima
    ), patch(
        "api.v1.routes_avisos.obtener_lista_avisos_activos", return_value=mock_avisos
    ), patch(
        "logic.financiero.obtener_cronograma_vencimientos",
        return_value=mock_vencimientos,
    ):
        res = client.get("/api/v1/bootstrap", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()

    # Verificación de headers de caché
    assert "no-store" in res.headers.get("Cache-Control", "")

    # 1. Resumen Financiero
    rf = data["resumen_financiero"]
    assert rf["saldo_acumulado"] == 3500000
    assert rf["margen_libre"] == 1850000
    assert rf["posicion_iva"] == 150000
    assert rf["es_debito_fiscal"] is False

    # 2. Asistencia
    asis = data["estado_asistencia_hoy"]
    assert asis["fecha"] == "04/11/2026"
    assert asis["estado"] == "TRABAJANDO"
    assert asis["hora_entrada"] == "08:00"
    assert asis["minutos_transcurridos"] == 120
    assert asis["puede_marcar_salida"] is True

    # 3. Clima
    clima = data["clima"]
    assert clima["temperatura"] == 25.5
    assert clima["llevar_paraguas"] is True
    assert clima["condicion"] == "Lluvia ligera"

    # 4. Avisos
    assert len(data["proximos_avisos"]) == 1
    assert data["proximos_avisos"][0]["id"] == "av-1"

    # 5. Vencimientos
    assert len(data["proximos_vencimientos"]) == 1
    assert data["proximos_vencimientos"][0]["id"] == "DEUDA-001"


def test_bootstrap_tolerancia_fallo_clima(client):
    """Verifica que un fallo en la API de clima retorne un fallback seguro sin abortar."""
    with patch(
        "logic.cron_jobs.obtener_datos_clima",
        side_effect=Exception("Timeout en Open-Meteo"),
    ):
        res = client.get("/api/v1/bootstrap", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    assert "clima" in data
    assert data["clima"]["condicion"] == "No disponible"
    assert data["clima"]["llevar_paraguas"] is False
    assert data["clima"]["temperatura"] == 0.0


def test_bootstrap_tolerancia_fallo_financiero(client):
    """Verifica que un fallo en el agente financiero no rompa el bootstrap."""
    with patch(
        "api.v1.routes_dashboard.calcular_resumen_financiero",
        side_effect=Exception("Sheets 503 Unavailable"),
    ):
        res = client.get("/api/v1/bootstrap", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    rf = data["resumen_financiero"]
    assert rf["saldo_acumulado"] == 0
    assert rf["ingresos"] == 0
    assert rf["margen_libre"] == 0


def test_bootstrap_tolerancia_fallo_asistencia(client):
    """Verifica que un fallo al consultar SQLite de asistencia degrade graciosamente."""
    with patch(
        "api.v1.routes_asistencia.obtener_estado_jornada_hoy_dto",
        side_effect=Exception("SQLite locked"),
    ), patch(
        "api.v1.routes_dashboard.get_now_py",
        return_value=datetime(2026, 11, 4, 10, 0, tzinfo=tz_py),
    ):
        res = client.get("/api/v1/bootstrap", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    asis = data["estado_asistencia_hoy"]
    assert asis["fecha"] == "04/11/2026"
    assert asis["estado"] == "PENDIENTE"
    assert asis["puede_marcar_entrada"] is True


def test_bootstrap_tolerancia_fallo_avisos_y_vencimientos(client):
    """Verifica que excepciones al leer avisos o deudas devuelvan listas vacías."""
    with patch(
        "api.v1.routes_avisos.obtener_lista_avisos_activos",
        side_effect=Exception("Corrupt JSON"),
    ), patch(
        "logic.financiero.obtener_cronograma_vencimientos",
        side_effect=Exception("Sheets rate limit"),
    ):
        res = client.get("/api/v1/bootstrap", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    assert data["proximos_avisos"] == []
    assert data["proximos_vencimientos"] == []


def test_bootstrap_fallo_total_subsistemas(client):
    """Verifica resiliencia absoluta: todos los servicios fallan pero el inicio no se bloquea."""
    with patch(
        "api.v1.routes_dashboard.calcular_resumen_financiero",
        side_effect=Exception("Finanzas caídas"),
    ), patch(
        "api.v1.routes_asistencia.obtener_estado_jornada_hoy_dto",
        side_effect=Exception("Asistencia caída"),
    ), patch(
        "logic.cron_jobs.obtener_datos_clima",
        side_effect=Exception("Clima caído"),
    ), patch(
        "api.v1.routes_avisos.obtener_lista_avisos_activos",
        side_effect=Exception("Avisos caídos"),
    ), patch(
        "logic.financiero.obtener_cronograma_vencimientos",
        side_effect=Exception("Vencimientos caídos"),
    ):
        res = client.get("/api/v1/bootstrap", headers=HEADERS)

    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data["resumen_financiero"], dict)
    assert isinstance(data["estado_asistencia_hoy"], dict)
    assert isinstance(data["clima"], dict)
    assert isinstance(data["proximos_avisos"], list)
    assert isinstance(data["proximos_vencimientos"], list)
