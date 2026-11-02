from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

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

from repositories.local_repository import LocalRepository  # noqa: E402
from services.sync_service import SyncService  # noqa: E402


@pytest.fixture
def client() -> Any:
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def local_repo_temp(tmp_path: Any) -> LocalRepository:
    db_file = tmp_path / "sync_test.db"
    return LocalRepository(db_path=db_file)


# ── Tests Unitarios de SyncService ──────────────────────────────────────────


def test_volcar_local_a_sheets_laboral_exitoso(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica que las jornadas con sincronizado_sheets=0 se vuelquen y marquen como sincronizadas=1."""
    # Insertar 2 jornadas pendientes
    local_repo_temp.obtener_o_crear_jornada(
        fecha="2026-11-02", dia="Lunes", modo="normal"
    )
    local_repo_temp.actualizar_jornada(
        fecha="2026-11-02",
        hora_entrada="08:00",
        hora_salida="17:00",
        horas_decimal=8.0,
        sincronizado_sheets=0,
    )

    local_repo_temp.obtener_o_crear_jornada(
        fecha="2026-11-03", dia="Martes", modo="normal"
    )
    local_repo_temp.actualizar_jornada(
        fecha="2026-11-03",
        hora_entrada="08:15",
        hora_salida="17:15",
        horas_decimal=8.0,
        sincronizado_sheets=0,
    )

    # Verificar que están pendientes
    pendientes_antes = local_repo_temp.listar_jornadas_pendientes_sincronizacion()
    assert len(pendientes_antes) == 2

    # Mockear Google Sheets
    mock_ws = MagicMock()
    mock_ws.title = "Noviembre 2026"
    mock_ws.col_values.return_value = ["Fecha"]  # Cabecera vacía sin registros

    mock_wb = MagicMock()
    mock_wb.worksheets.return_value = [mock_ws]
    mock_wb.worksheet.return_value = mock_ws

    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_wb

    with patch("logic.logic.ConexionSheets.obtener_cliente", return_value=mock_client):
        service = SyncService(
            local_repo=local_repo_temp, spreadsheet_id="test_sheet_id"
        )
        res = service.volcar_local_a_sheets(modulo="laboral")

        assert res["exito"] is True
        assert res["registros_sincronizados"] == 2
        assert mock_ws.append_row.call_count == 2

        # Verificar que en SQLite ahora están sincronizadas (0 pendientes)
        pendientes_despues = local_repo_temp.listar_jornadas_pendientes_sincronizacion()
        assert len(pendientes_despues) == 0

        j1 = local_repo_temp.obtener_jornada_por_fecha("2026-11-02")
        assert j1 is not None and j1["sincronizado_sheets"] == 1


def test_volcar_sheets_a_local_laboral_exitoso(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica que las filas de Google Sheets se importen a SQLite local marcando sincronizado_sheets=1."""
    mock_ws = MagicMock()
    mock_ws.title = "Noviembre 2026"
    mock_ws.get_all_values.return_value = [
        [
            "Dia",
            "Fecha",
            "Hora entrada",
            "Salgo almuerzo",
            "Vuelta almuerzo",
            "Hora salida",
            "Horas",
        ],
        ["Lunes", "02/11/2026", "08:00", "12:00", "13:00", "17:00", "8.0"],
        ["Martes", "03/11/2026", "08:30", "", "", "17:30", "9.0"],
    ]

    mock_wb = MagicMock()
    mock_wb.worksheets.return_value = [mock_ws]
    mock_wb.worksheet.return_value = mock_ws

    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_wb

    with patch("logic.logic.ConexionSheets.obtener_cliente", return_value=mock_client):
        service = SyncService(
            local_repo=local_repo_temp, spreadsheet_id="test_sheet_id"
        )
        res = service.volcar_sheets_a_local(mes=11, anio=2026, modulo="laboral")

        assert res["exito"] is True
        assert res["registros_sincronizados"] == 2

        # Verificar en SQLite
        j1 = local_repo_temp.obtener_jornada_por_fecha("2026-11-02")
        assert j1 is not None
        assert j1["hora_entrada"] == "08:00"
        assert j1["hora_salida"] == "17:00"
        assert j1["horas_decimal"] == 8.0
        assert j1["sincronizado_sheets"] == 1

        j2 = local_repo_temp.obtener_jornada_por_fecha("2026-11-03")
        assert j2 is not None
        assert j2["hora_entrada"] == "08:30"
        assert j2["horas_decimal"] == 9.0


def test_volcar_local_a_sheets_resiliencia_falla(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica que si falla la conexión a Google Sheets, no se marque como sincronizado en local."""
    local_repo_temp.obtener_o_crear_jornada(
        fecha="2026-11-04", dia="Miércoles", modo="normal"
    )
    local_repo_temp.actualizar_jornada(
        fecha="2026-11-04",
        hora_entrada="08:00",
        hora_salida="17:00",
        sincronizado_sheets=0,
    )

    with patch("logic.logic.ConexionSheets.obtener_cliente", return_value=None):
        service = SyncService(
            local_repo=local_repo_temp, spreadsheet_id="test_sheet_id"
        )
        res = service.volcar_local_a_sheets(modulo="laboral")

        assert res["exito"] is False
        assert res["registros_sincronizados"] == 0
        assert "No se pudo autorizar cliente" in res["detalles"]

        # La jornada local sigue intacta y pendiente
        pendientes = local_repo_temp.listar_jornadas_pendientes_sincronizacion()
        assert len(pendientes) == 1
        assert pendientes[0]["fecha"] == "2026-11-04"


def test_volcar_local_a_sheets_materias(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica el volcado de materias universitarias a Google Sheets."""
    m_id = local_repo_temp.registrar_asistencia_materia(
        fecha="2026-11-02",
        dia="Lunes",
        materia="Inteligencia Artificial",
        tipo_turno="Teoria",
        hora_entrada="18:30",
        presente=1,
        sincronizado_sheets=0,
    )
    assert m_id > 0

    mock_ws = MagicMock()
    mock_ws.title = "Inteligencia Artificial"
    mock_ws.col_values.return_value = ["Fecha"]

    mock_wb = MagicMock()
    mock_wb.worksheets.return_value = [mock_ws]
    mock_wb.worksheet.return_value = mock_ws

    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_wb

    with patch("logic.logic.ConexionSheets.obtener_cliente", return_value=mock_client):
        service = SyncService(
            local_repo=local_repo_temp, spreadsheet_id="test_sheet_id"
        )
        res = service.volcar_local_a_sheets(modulo="materias")

        assert res["exito"] is True
        assert res["registros_sincronizados"] == 1

        pendientes = local_repo_temp.listar_materias_pendientes_sincronizacion()
        assert len(pendientes) == 0


# ── Tests de Endpoint REST: POST /api/v1/asistencia/sync ───────────────────


def test_endpoint_asistencia_sync_unauthorized(client: Any) -> None:
    """Verifica 401 Unauthorized si falta la API Key."""
    res = client.post("/api/v1/asistencia/sync")
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_endpoint_asistencia_sync_validation_error(client: Any) -> None:
    """Verifica 400 Bad Request si los parámetros no cumplen con el schema SyncRequest."""
    res = client.post(
        "/api/v1/asistencia/sync",
        headers={"X-API-KEY": "test-secret-key"},
        json={"direccion": "invalida_direccion"},
    )
    assert res.status_code == 400
    assert res.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_endpoint_asistencia_sync_local_to_sheets_success(client: Any) -> None:
    """Verifica invocación exitosa de sincronización local -> sheets vía REST."""
    mock_result = {
        "exito": True,
        "registros_sincronizados": 3,
        "detalles": "Volcado completado exitosamente: 3 registros.",
    }

    with patch(
        "services.sync_service.SyncService.volcar_local_a_sheets",
        return_value=mock_result,
    ):
        res = client.post(
            "/api/v1/asistencia/sync",
            headers={"X-API-KEY": "test-secret-key"},
            json={
                "direccion": "local_to_sheets",
                "modulo": "laboral",
                "mes": 11,
                "anio": 2026,
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["exito"] is True
        assert data["registros_sincronizados"] == 3
        assert "Volcado completado" in data["detalles"]


def test_endpoint_asistencia_sync_sheets_to_local_success(client: Any) -> None:
    """Verifica invocación exitosa de sincronización sheets -> local vía REST."""
    mock_result = {
        "exito": True,
        "registros_sincronizados": 5,
        "detalles": "Importación completada exitosamente: 5 registros.",
    }

    with patch(
        "services.sync_service.SyncService.volcar_sheets_a_local",
        return_value=mock_result,
    ):
        res = client.post(
            "/api/v1/asistencia/sync",
            headers={"X-API-KEY": "test-secret-key"},
            json={
                "direccion": "sheets_to_local",
                "modulo": "todo",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["exito"] is True
        assert data["registros_sincronizados"] == 5


def test_endpoint_asistencia_sync_failure_returns_502(client: Any) -> None:
    """Verifica que si la sincronización falla con Google Sheets, retorne HTTP 502."""
    mock_result = {
        "exito": False,
        "registros_sincronizados": 0,
        "detalles": "Error conectando con Google Sheets: Timeout",
    }

    with patch(
        "services.sync_service.SyncService.volcar_local_a_sheets",
        return_value=mock_result,
    ):
        res = client.post(
            "/api/v1/asistencia/sync",
            headers={"X-API-KEY": "test-secret-key"},
            json={
                "direccion": "local_to_sheets",
            },
        )
        assert res.status_code == 502
        data = res.get_json()
        assert data["exito"] is False
        assert data["registros_sincronizados"] == 0
