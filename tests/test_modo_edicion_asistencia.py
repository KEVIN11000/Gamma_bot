from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from repositories.local_repository import LocalRepository
from services.asistencia_service import (
    _step_capturar_horarios_rectificar,
    _step_verificar_clave_edicion,
    iniciar_flujo_edicion_asistencia,
    limpiar_salida_jornada,
    procesar_callback_edicion_asistencia,
    rectificar_jornada_asistencia,
)


@pytest.fixture
def local_repo_temp(tmp_path: Any) -> LocalRepository:
    db_file = tmp_path / "edicion_asist_test.db"
    return LocalRepository(db_path=db_file)


# ── Tests Unitarios de Servicios de Edición de Asistencia ─────────────────────


def test_limpiar_salida_jornada_inexistente(
    local_repo_temp: LocalRepository,
) -> None:
    res = limpiar_salida_jornada(
        fecha="2026-11-05", repo=local_repo_temp, sync_sheets=False
    )
    assert res["exito"] is False
    assert "No existe registro" in res["mensaje"]


def test_limpiar_salida_jornada_sin_salida(
    local_repo_temp: LocalRepository,
) -> None:
    local_repo_temp.obtener_o_crear_jornada("2026-11-05", "Jueves", modo="normal")
    local_repo_temp.actualizar_jornada("2026-11-05", hora_entrada="08:45")

    res = limpiar_salida_jornada(
        fecha="2026-11-05", repo=local_repo_temp, sync_sheets=False
    )
    assert res["exito"] is False
    assert "No hay salida registrada" in res["mensaje"]


def test_limpiar_salida_jornada_exitosa(
    local_repo_temp: LocalRepository,
) -> None:
    local_repo_temp.obtener_o_crear_jornada("2026-11-05", "Jueves", modo="normal")
    local_repo_temp.actualizar_jornada(
        "2026-11-05",
        hora_entrada="08:45",
        hora_salida="15:09",
        horas_decimal=6.4,
    )

    mock_sync_result = {
        "exito": True,
        "registros_sincronizados": 1,
        "detalles": "OK",
    }
    with (
        patch.dict(os.environ, {"SPREADSHEET_ID": "mock_sheet_id"}),
        patch(
            "services.sync_service.SyncService.volcar_local_a_sheets",
            return_value=mock_sync_result,
        ) as mock_volcar,
    ):
        res = limpiar_salida_jornada(
            fecha="2026-11-05", repo=local_repo_temp, sync_sheets=True
        )

        assert res["exito"] is True
        assert "15:09" in res["mensaje"]
        assert res["sincronizado_sheets"] is True

        # Verificar en SQLite
        jornada = local_repo_temp.obtener_jornada_por_fecha("2026-11-05")
        assert jornada is not None
        assert jornada["hora_entrada"] == "08:45"
        assert jornada["hora_salida"] is None
        assert jornada["horas_decimal"] == 0.0

        mock_volcar.assert_called_once_with(
            mes=11, anio=2026, modulo="laboral", forzar=True
        )


def test_rectificar_jornada_asistencia_servicio(
    local_repo_temp: LocalRepository,
) -> None:
    mock_sync_result = {
        "exito": True,
        "registros_sincronizados": 1,
        "detalles": "OK",
    }
    with (
        patch.dict(os.environ, {"SPREADSHEET_ID": "mock_sheet_id"}),
        patch(
            "services.sync_service.SyncService.volcar_local_a_sheets",
            return_value=mock_sync_result,
        ) as mock_volcar,
    ):
        res = rectificar_jornada_asistencia(
            fecha="2026-11-04",
            hora_entrada="08:45",
            hora_salida_almuerzo="12:00",
            hora_vuelta_almuerzo="13:00",
            hora_salida="17:06",
            modo="normal",
            sync_sheets=True,
            repo=local_repo_temp,
        )

        assert res["exito"] is True
        assert res["horas_decimal"] == 7.35
        assert res["sincronizado_sheets"] is True

        jornada = local_repo_temp.obtener_jornada_por_fecha("2026-11-04")
        assert jornada is not None
        assert jornada["hora_entrada"] == "08:45"
        assert jornada["hora_salida_almuerzo"] == "12:00"
        assert jornada["hora_vuelta_almuerzo"] == "13:00"
        assert jornada["hora_salida"] == "17:06"
        assert jornada["horas_decimal"] == 7.35
        mock_volcar.assert_called_once_with(
            mes=11, anio=2026, modulo="laboral", forzar=True
        )


# ── Tests de Handlers Conversacionales de Telegram ───────────────────────────


def test_iniciar_flujo_edicion_asistencia_pide_clave() -> None:
    mock_bot = MagicMock()
    iniciar_flujo_edicion_asistencia(mock_bot, chat_id=12345)
    mock_bot.send_message.assert_called_once()
    assert "Modo Edición" in mock_bot.send_message.call_args[0][1]
    mock_bot.register_next_step_handler.assert_called_once()


def test_step_verificar_clave_invalida() -> None:
    mock_bot = MagicMock()
    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.message_id = 999
    mock_msg.text = "clave_erronea"

    with patch.dict(os.environ, {"X_API_KEY": "clave_secreta_real"}):
        _step_verificar_clave_edicion(mock_msg, mock_bot)

    mock_bot.delete_message.assert_called_once_with(12345, 999)
    mock_bot.send_message.assert_called_once()
    assert "Acceso denegado" in mock_bot.send_message.call_args[0][1]


def test_step_verificar_clave_valida_muestra_menu() -> None:
    mock_bot = MagicMock()
    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.message_id = 999
    mock_msg.text = "clave_secreta_real"

    with patch.dict(os.environ, {"X_API_KEY": "clave_secreta_real"}):
        _step_verificar_clave_edicion(mock_msg, mock_bot)

    mock_bot.delete_message.assert_called_once_with(12345, 999)
    mock_bot.send_message.assert_called_once()
    args, kwargs = mock_bot.send_message.call_args
    assert "Modo Edición Habilitado" in args[1]
    assert kwargs.get("reply_markup") is not None


def test_procesar_callback_cancelar() -> None:
    mock_bot = MagicMock()
    mock_call = MagicMock()
    mock_call.data = "edit_asist:cancelar"
    mock_call.message.chat.id = 12345
    mock_call.message.message_id = 888

    procesar_callback_edicion_asistencia(mock_call, mock_bot)
    mock_bot.edit_message_text.assert_called_once()
    assert "finalizada" in mock_bot.edit_message_text.call_args[0][0]


def test_procesar_callback_limpiar_hoy_exitoso(
    local_repo_temp: LocalRepository,
) -> None:
    local_repo_temp.obtener_o_crear_jornada("2026-11-05", "Jueves", modo="normal")
    local_repo_temp.actualizar_jornada(
        "2026-11-05",
        hora_entrada="08:45",
        hora_salida="15:09",
        horas_decimal=6.4,
    )

    mock_bot = MagicMock()
    mock_call = MagicMock()
    mock_call.data = "edit_asist:limpiar_hoy"
    mock_call.message.chat.id = 12345
    mock_call.message.message_id = 888

    with (
        patch(
            "repositories.local_repository.get_local_repository",
            return_value=local_repo_temp,
        ),
        patch("services.asistencia_service.limpiar_salida_jornada") as mock_limpiar,
    ):
        mock_limpiar.return_value = {
            "exito": True,
            "mensaje": "Salida (15:09) eliminada correctamente.",
            "sincronizado_sheets": True,
        }
        procesar_callback_edicion_asistencia(mock_call, mock_bot)

    mock_limpiar.assert_called_once()
    assert mock_bot.edit_message_text.call_count >= 2


def test_step_capturar_horarios_rectificar_exitoso(
    local_repo_temp: LocalRepository,
) -> None:
    mock_bot = MagicMock()
    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.message_id = 999
    mock_msg.text = "08:45, 12:00, 13:00, 17:06"

    mock_espera = MagicMock()
    mock_espera.message_id = 777
    mock_bot.send_message.return_value = mock_espera

    with patch(
        "services.asistencia_service.rectificar_jornada_asistencia"
    ) as mock_rect:
        mock_rect.return_value = {
            "exito": True,
            "horas_decimal": 7.35,
            "sincronizado_sheets": True,
        }
        _step_capturar_horarios_rectificar(mock_msg, mock_bot, "2026-11-04")

    mock_rect.assert_called_once_with(
        fecha="2026-11-04",
        hora_entrada="08:45",
        hora_salida_almuerzo="12:00",
        hora_vuelta_almuerzo="13:00",
        hora_salida="17:06",
        modo="normal",
        sync_sheets=True,
    )
    mock_bot.edit_message_text.assert_called_once()
    assert "rectificada con éxito" in mock_bot.edit_message_text.call_args[0][0]
