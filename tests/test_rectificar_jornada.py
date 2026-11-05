from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

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

with (
    patch("com.bot.GAMMA") as MockGamma,
    patch("logic.cron_jobs.notificacion_clima"),
    patch("logic.cron_jobs.resumen_semanal"),
    patch("logic.cron_jobs.rotar_logs"),
):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402

from api.schemas import JornadaRectificarRequest, JornadaRectificarResponse
from repositories.local_repository import LocalRepository


@pytest.fixture
def client() -> Any:
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def local_repo_temp(tmp_path: Any) -> LocalRepository:
    db_file = tmp_path / "rectificar_test.db"
    return LocalRepository(db_path=db_file)


# ── Tests de Esquemas y Validaciones Pydantic ────────────────────────────────


def test_jornada_rectificar_request_valido() -> None:
    req = JornadaRectificarRequest(
        hora_entrada="08:30",
        hora_salida_almuerzo="12:00",
        hora_vuelta_almuerzo="13:00",
        hora_salida="17:30",
        modo="normal",
        sincronizar_sheets=True,
    )
    assert req.hora_entrada == "08:30"
    assert req.hora_salida == "17:30"
    assert req.modo == "normal"
    assert req.sincronizar_sheets is True


def test_jornada_rectificar_request_horas_vacias_o_none() -> None:
    req = JornadaRectificarRequest(
        hora_entrada="  08:45  ",
        hora_salida_almuerzo="",
        hora_vuelta_almuerzo=None,
        hora_salida="18:00",
    )
    assert req.hora_entrada == "08:45"
    assert req.hora_salida_almuerzo is None
    assert req.hora_vuelta_almuerzo is None
    assert req.hora_salida == "18:00"


def test_jornada_rectificar_request_formato_hora_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        JornadaRectificarRequest(hora_entrada="25:99")
    assert "Formato de hora inválido" in str(exc.value)

    with pytest.raises(ValidationError) as exc2:
        JornadaRectificarRequest(hora_salida="8:30")
    assert "Formato de hora inválido" in str(exc2.value)


def test_jornada_rectificar_request_salida_menor_entrada() -> None:
    with pytest.raises(ValidationError) as exc:
        JornadaRectificarRequest(
            hora_entrada="18:00",
            hora_salida="09:00",
        )
    assert "La hora de salida no puede ser anterior a la hora de entrada" in str(
        exc.value
    )


def test_jornada_rectificar_request_almuerzo_inconsistente() -> None:
    with pytest.raises(ValidationError) as exc:
        JornadaRectificarRequest(
            hora_salida_almuerzo="13:00",
            hora_vuelta_almuerzo="12:30",
        )
    assert "La vuelta de almuerzo no puede ser anterior a la salida de almuerzo" in str(
        exc.value
    )


def test_jornada_rectificar_request_modo_invalido() -> None:
    with pytest.raises(ValidationError) as exc:
        JornadaRectificarRequest(modo="invalido")
    assert "El modo debe ser 'normal' o 'directo'" in str(exc.value)


def test_jornada_rectificar_response_dto() -> None:
    res = JornadaRectificarResponse(
        status="ok",
        fecha="2026-11-04",
        dia="Miércoles",
        modo="directo",
        hora_entrada="08:30",
        hora_salida_almuerzo=None,
        hora_vuelta_almuerzo=None,
        hora_salida="17:00",
        horas_decimal=8.5,
        sincronizado_sheets=True,
        mensaje="Jornada actualizada y sincronizada",
    )
    assert res.fecha == "2026-11-04"
    assert res.horas_decimal == 8.5
    assert res.sincronizado_sheets is True


# ── Tests de Endpoint REST: PUT /api/v1/asistencia/jornadas/<fecha> ──────────


def test_endpoint_rectificar_jornada_unauthorized(client: Any) -> None:
    """Verifica 401 si falta la API Key."""
    res = client.put("/api/v1/asistencia/jornadas/2026-11-04", json={})
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_endpoint_rectificar_jornada_invalid_date(client: Any) -> None:
    """Verifica 400 si la fecha no cumple el formato YYYY-MM-DD."""
    res = client.put(
        "/api/v1/asistencia/jornadas/fecha-invalida",
        headers={"X-API-KEY": "test-secret-key"},
        json={"hora_entrada": "08:30"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "INVALID_DATE_FORMAT"


def test_endpoint_rectificar_jornada_validation_error(client: Any) -> None:
    """Verifica 400 si el payload contiene horarios inconsistentes."""
    res = client.put(
        "/api/v1/asistencia/jornadas/2026-11-04",
        headers={"X-API-KEY": "test-secret-key"},
        json={"hora_entrada": "19:00", "hora_salida": "08:00"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_endpoint_rectificar_jornada_success_sin_sheets(
    client: Any, local_repo_temp: LocalRepository
) -> None:
    """Verifica rectificación exitosa en SQLite sin sincronizar a Sheets."""
    with patch(
        "repositories.local_repository.get_local_repository",
        return_value=local_repo_temp,
    ):
        payload = {
            "hora_entrada": "08:45",
            "hora_salida": "17:15",
            "modo": "directo",
            "sincronizar_sheets": False,
        }
        res = client.put(
            "/api/v1/asistencia/jornadas/2026-11-04",
            headers={"X-API-KEY": "test-secret-key"},
            json=payload,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"
        assert data["fecha"] == "2026-11-04"
        assert data["dia"] == "Miércoles"
        assert data["hora_entrada"] == "08:45"
        assert data["hora_salida"] == "17:15"
        assert data["horas_decimal"] == 8.5
        assert data["sincronizado_sheets"] is False

        # Verificar persistencia en base de datos SQLite
        guardado = local_repo_temp.obtener_jornada_por_fecha("2026-11-04")
        assert guardado is not None
        assert guardado["hora_entrada"] == "08:45"
        assert guardado["hora_salida"] == "17:15"
        assert guardado["horas_decimal"] == 8.5


def test_endpoint_rectificar_jornada_success_con_sheets(
    client: Any, local_repo_temp: LocalRepository
) -> None:
    """Verifica rectificación exitosa en SQLite con write-through a Sheets."""
    mock_sync_result = {
        "exito": True,
        "registros_sincronizados": 1,
        "detalles": "Volcado exitoso",
    }
    with (
        patch(
            "repositories.local_repository.get_local_repository",
            return_value=local_repo_temp,
        ),
        patch.dict(os.environ, {"SPREADSHEET_ID": "mock_spreadsheet_id"}),
        patch(
            "services.sync_service.SyncService.volcar_local_a_sheets",
            return_value=mock_sync_result,
        ) as mock_volcar,
    ):
        payload = {
            "hora_entrada": "09:00",
            "hora_salida_almuerzo": "12:30",
            "hora_vuelta_almuerzo": "13:30",
            "hora_salida": "18:00",
            "modo": "normal",
            "sincronizar_sheets": True,
        }
        res = client.put(
            "/api/v1/asistencia/jornadas/2026-11-04",
            headers={"X-API-KEY": "test-secret-key"},
            json=payload,
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["sincronizado_sheets"] is True
        assert data["horas_decimal"] == 8.0
        mock_volcar.assert_called_once_with(
            mes=11, anio=2026, modulo="laboral", forzar=True
        )
