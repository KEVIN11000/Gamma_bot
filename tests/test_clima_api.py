from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

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
def client() -> Any:
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_unauthorized_clima(client: Any) -> None:
    """Verifica que /api/v1/clima exija autenticación X-API-KEY."""
    res = client.get("/api/v1/clima")
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_get_clima_umbrella_required_high(client: Any) -> None:
    """Verifica respuesta exitosa con alerta de paraguas alta (probabilidad >= 60%)."""
    fake_open_meteo_response = {
        "daily": {
            "weathercode": [63],
            "temperature_2m_max": [28.4],
            "temperature_2m_min": [19.1],
            "precipitation_probability_max": [75],
            "windspeed_10m_max": [16.2],
        },
        "current_weather": {
            "temperature": 23.5,
            "windspeed": 14.0,
            "weathercode": 63,
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_open_meteo_response

    with patch("requests.get", return_value=mock_resp):
        res = client.get("/api/v1/clima", headers={"X-API-KEY": "test-secret-key"})
        assert res.status_code == 200
        data = res.get_json()

        assert data["temperatura_actual"] == 23.5
        assert data["temperatura_min"] == 19.1
        assert data["temperatura_max"] == 28.4
        assert data["condicion"] == "Lluvia moderada"
        assert "actualizado_at" in data

        alerta = data["alerta_paraguas"]
        assert alerta["necesita_paraguas"] is True
        assert alerta["probabilidad_lluvia"] == 75
        assert "Alta probabilidad de lluvia" in alerta["motivo"]


def test_get_clima_umbrella_required_threshold_35(client: Any) -> None:
    """Verifica alerta de paraguas en el umbral medio (35% <= prob < 60%)."""
    fake_open_meteo_response = {
        "daily": {
            "weathercode": [80],
            "temperature_2m_max": [31.0],
            "temperature_2m_min": [22.0],
            "precipitation_probability_max": [35],
            "windspeed_10m_max": [12.0],
        },
        "current_weather": {
            "temperature": 29.0,
            "windspeed": 10.0,
            "weathercode": 80,
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_open_meteo_response

    with patch("requests.get", return_value=mock_resp):
        res = client.get("/api/v1/clima", headers={"X-API-KEY": "test-secret-key"})
        assert res.status_code == 200
        data = res.get_json()

        assert data["temperatura_actual"] == 29.0
        assert data["condicion"] == "Lluvia con chaparrones"
        alerta = data["alerta_paraguas"]
        assert alerta["necesita_paraguas"] is True
        assert alerta["probabilidad_lluvia"] == 35
        assert "Posibles lluvias por la tarde" in alerta["motivo"]


def test_get_clima_no_umbrella_needed(client: Any) -> None:
    """Verifica respuesta cuando la probabilidad de lluvia es menor a 35%."""
    fake_open_meteo_response = {
        "daily": {
            "weathercode": [0],
            "temperature_2m_max": [33.5],
            "temperature_2m_min": [21.5],
            "precipitation_probability_max": [15],
            "windspeed_10m_max": [9.5],
        },
        "current_weather": {
            "temperature": 32.0,
            "windspeed": 8.0,
            "weathercode": 0,
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_open_meteo_response

    with patch("requests.get", return_value=mock_resp):
        res = client.get("/api/v1/clima", headers={"X-API-KEY": "test-secret-key"})
        assert res.status_code == 200
        data = res.get_json()

        assert data["temperatura_actual"] == 32.0
        assert data["condicion"] == "Despejado"
        alerta = data["alerta_paraguas"]
        assert alerta["necesita_paraguas"] is False
        assert alerta["probabilidad_lluvia"] == 15
        assert "Baja probabilidad" in alerta["motivo"]


def test_get_clima_fallback_on_network_error(client: Any) -> None:
    """Verifica resiliencia ante falla de conexión con Open-Meteo."""
    with patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectTimeout("Conexión expirada"),
    ):
        res = client.get("/api/v1/clima", headers={"X-API-KEY": "test-secret-key"})
        assert res.status_code == 200
        data = res.get_json()

        assert data["temperatura_actual"] == 0.0
        assert data["condicion"] == "Servicio no disponible"
        assert data["alerta_paraguas"]["necesita_paraguas"] is False
        assert data["alerta_paraguas"]["probabilidad_lluvia"] == 0
        assert "No se pudo consultar" in data["alerta_paraguas"]["motivo"]


def test_cron_notificacion_clima_reutilizacion() -> None:
    """Verifica que notificacion_clima consuma correctamente obtener_datos_clima."""
    from logic.cron_jobs import notificacion_clima

    mock_bot = MagicMock()
    fake_datos = {
        "temperatura_actual": 25.0,
        "temperatura_min": 18.0,
        "temperatura_max": 29.0,
        "condicion": "Parcialmente nublado",
        "alerta_paraguas": {
            "necesita_paraguas": True,
            "probabilidad_lluvia": 50,
            "motivo": "Posibles lluvias por la tarde. Lleva el paraguas por las dudas.",
        },
        "actualizado_at": "2026-11-02T07:00:00",
        "viento": 14.0,
        "emoji": "⛅",
    }

    with patch("logic.cron_jobs.obtener_datos_clima", return_value=fake_datos):
        exito = notificacion_clima(mock_bot, 123456)
        assert exito is True
        mock_bot.send_message.assert_called_once()
        msg_text = mock_bot.send_message.call_args[0][1]
        assert "Parcialmente nublado" in msg_text
        assert "18°C — 29°C" in msg_text
        assert "50%" in msg_text
        assert "Posibles lluvias por la tarde" in msg_text


def test_cron_notificacion_clima_aborta_si_falla_servicio() -> None:
    """Verifica que el cron aborte limpiamente si el servicio meteorológico está caído."""
    from logic.cron_jobs import notificacion_clima

    mock_bot = MagicMock()
    fake_fallback = {
        "temperatura_actual": 0.0,
        "temperatura_min": 0.0,
        "temperatura_max": 0.0,
        "condicion": "Servicio no disponible",
        "alerta_paraguas": {
            "necesita_paraguas": False,
            "probabilidad_lluvia": 0,
            "motivo": "No se pudo consultar el servicio meteorológico.",
        },
        "actualizado_at": "2026-11-02T07:00:00",
        "viento": 0.0,
        "emoji": "🌡️",
    }

    with patch("logic.cron_jobs.obtener_datos_clima", return_value=fake_fallback):
        exito = notificacion_clima(mock_bot, 123456)
        assert exito is False
        mock_bot.send_message.assert_not_called()
