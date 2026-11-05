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


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


HEADERS = {"X-API-KEY": "test-secret-key"}
tz_py = pytz.timezone("America/Asuncion")


def test_estado_hoy_unauthorized(client):
    res = client.get("/api/v1/asistencia/estado-hoy")
    assert res.status_code == 401


@patch("api.v1.routes_asistencia.get_now_py")
@patch("repositories.local_repository.LocalRepository.obtener_jornada_por_fecha")
def test_estado_hoy_pendiente_laboral(mock_get_jornada, mock_now, client):
    # Miércoles 04/11/2026 a las 07:30
    fixed_now = datetime(2026, 11, 4, 7, 30, tzinfo=tz_py)
    mock_now.return_value = fixed_now
    mock_get_jornada.return_value = None

    res = client.get("/api/v1/asistencia/estado-hoy", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["fecha"] == "04/11/2026"
    assert data["estado"] == "PENDIENTE"
    assert data["hora_entrada"] is None
    assert data["hora_salida"] is None
    assert data["puede_marcar_entrada"] is True
    assert data["puede_marcar_salida"] is False
    assert data["es_feriado_o_descanso"] is False


@patch("api.v1.routes_asistencia.get_now_py")
@patch("repositories.local_repository.LocalRepository.obtener_jornada_por_fecha")
def test_estado_hoy_dia_libre_fin_de_semana(mock_get_jornada, mock_now, client):
    # Domingo 08/11/2026
    fixed_now = datetime(2026, 11, 8, 10, 0, tzinfo=tz_py)
    mock_now.return_value = fixed_now
    mock_get_jornada.return_value = None

    res = client.get("/api/v1/asistencia/estado-hoy", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["fecha"] == "08/11/2026"
    assert data["estado"] == "LIBRE"
    assert data["es_feriado_o_descanso"] is True
    assert data["puede_marcar_entrada"] is False


@patch("api.v1.routes_asistencia.get_now_py")
@patch("repositories.local_repository.LocalRepository.obtener_jornada_por_fecha")
def test_estado_hoy_trabajando(mock_get_jornada, mock_now, client):
    # Entrada a las 08:00, hora actual 11:15 -> 195 minutos (3h 15m)
    fixed_now = datetime(2026, 11, 4, 11, 15, tzinfo=tz_py)
    mock_now.return_value = fixed_now
    mock_get_jornada.return_value = {
        "fecha": "2026-11-04",
        "hora_entrada": "08:00",
        "hora_salida": None,
    }

    res = client.get("/api/v1/asistencia/estado-hoy", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["estado"] == "TRABAJANDO"
    assert data["hora_entrada"] == "08:00"
    assert data["hora_salida"] is None
    assert data["minutos_transcurridos"] == 195
    assert data["tiempo_transcurrido_formato"] == "3h 15m"
    assert data["puede_marcar_entrada"] is False
    assert data["puede_marcar_salida"] is True


@patch("api.v1.routes_asistencia.get_now_py")
@patch("repositories.local_repository.LocalRepository.obtener_jornada_por_fecha")
def test_estado_hoy_completado(mock_get_jornada, mock_now, client):
    # Entrada 08:00, Salida 17:00, horas_decimal = 8.5 (8h 30m)
    fixed_now = datetime(2026, 11, 4, 18, 0, tzinfo=tz_py)
    mock_now.return_value = fixed_now
    mock_get_jornada.return_value = {
        "fecha": "2026-11-04",
        "hora_entrada": "08:00",
        "hora_salida": "17:00",
        "horas_decimal": 8.5,
    }

    res = client.get("/api/v1/asistencia/estado-hoy", headers=HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["estado"] == "COMPLETADO"
    assert data["hora_entrada"] == "08:00"
    assert data["hora_salida"] == "17:00"
    assert data["minutos_transcurridos"] == 510
    assert data["tiempo_transcurrido_formato"] == "8h 30m"
    assert data["puede_marcar_entrada"] is False
    assert data["puede_marcar_salida"] is False


@patch("repositories.local_repository.LocalRepository.obtener_jornada_por_fecha")
def test_estado_hoy_error_interno(mock_get_jornada, client):
    mock_get_jornada.side_effect = RuntimeError("SQLite corrupto")
    res = client.get("/api/v1/asistencia/estado-hoy", headers=HEADERS)
    assert res.status_code == 500
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "INTERNAL_ERROR"
