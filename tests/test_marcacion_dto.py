from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from logic.constants import MarcacionResult
from logic.logic import AgenteAutonomoHoras
from repositories.local_repository import LocalRepository


@pytest.fixture
def test_repo(tmp_path: Path) -> LocalRepository:
    """Instancia limpia de LocalRepository aislada en disco temporal."""
    db_file = tmp_path / "test_marcacion.db"
    return LocalRepository(db_path=db_file)


@pytest.fixture
def agente(test_repo: LocalRepository) -> AgenteAutonomoHoras:
    """Instancia de AgenteAutonomoHoras conectada al test_repo."""
    return AgenteAutonomoHoras(spreadsheet_id="test_sheet_id", local_repo=test_repo)


def test_marcacion_result_dto_structure():
    """Valida la inmutabilidad, tipado y métodos de conversión del DTO puro MarcacionResult."""
    res = MarcacionResult(
        exito=True,
        tipo="entrada",
        hora="08:15",
        mensaje="✅ *Entrada* registrado a las 08:15.",
        auto_corte=False,
        datos_jornada={"id": 1, "modo": "normal"},
    )

    assert res.exito is True
    assert res.tipo == "entrada"
    assert res.hora == "08:15"
    assert "Entrada" in res.mensaje
    assert res.auto_corte is False
    assert res.datos_jornada == {"id": 1, "modo": "normal"}

    # Serialización to_dict
    d = res.to_dict()
    assert isinstance(d, dict)
    assert d["tipo"] == "entrada"
    assert d["hora"] == "08:15"

    # Default None en datos_jornada
    res_none = MarcacionResult(
        exito=False,
        tipo="error",
        hora="09:00",
        mensaje="Error prueba",
        datos_jornada=None,
    )
    assert res_none.datos_jornada == {}

    # Formateo para Telegram y __str__
    assert res.formatear_telegram() == "✅ *Entrada* registrado a las 08:15."
    assert str(res) == "✅ *Entrada* registrado a las 08:15."


def test_agente_horas_marcar_jornada_normal(
    agente: AgenteAutonomoHoras, test_repo: LocalRepository
):
    """Verifica el flujo secuencial completo de 4 puntos en modo normal sobre persistencia local."""
    fecha = "2026-11-02"

    # 1. Entrada
    res1 = agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="08:00")
    assert isinstance(res1, MarcacionResult)
    assert res1.exito is True
    assert res1.tipo == "entrada"
    assert res1.hora == "08:00"
    assert res1.datos_jornada["hora_entrada"] == "08:00"
    assert res1.datos_jornada["sincronizado_sheets"] == 0

    # 2. Salida a Almuerzo
    res2 = agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="12:00")
    assert res2.exito is True
    assert res2.tipo == "salida_almuerzo"
    assert res2.hora == "12:00"
    assert res2.datos_jornada["hora_salida_almuerzo"] == "12:00"

    # 3. Vuelta de Almuerzo
    res3 = agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="13:00")
    assert res3.exito is True
    assert res3.tipo == "vuelta_almuerzo"
    assert res3.hora == "13:00"
    assert res3.datos_jornada["hora_vuelta_almuerzo"] == "13:00"

    # 4. Salida
    res4 = agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="17:00")
    assert res4.exito is True
    assert res4.tipo == "salida"
    assert res4.hora == "17:00"
    assert res4.datos_jornada["hora_salida"] == "17:00"
    # Cálculo de horas: (12:00 - 08:00) + (17:00 - 13:00) = 4 + 4 = 8.0 horas
    assert res4.datos_jornada["horas_decimal"] == 8.0

    # 5. Intento posterior al cierre de los 4 puntos
    res5 = agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="17:15")
    assert res5.exito is False
    assert res5.tipo == "info"
    assert "completaste" in res5.mensaje


def test_agente_horas_marcar_jornada_directo(agente: AgenteAutonomoHoras):
    """Verifica el flujo directo (2 puntos: entrada y salida) y cálculo de horas corridas."""
    fecha = "2026-11-03"

    # 1. Entrada
    res1 = agente.ejecutar_marcado_para_bot(modo="directo", fecha=fecha, hora="08:30")
    assert res1.exito is True
    assert res1.tipo == "entrada"
    assert res1.hora == "08:30"

    # 2. Salida
    res2 = agente.ejecutar_marcado_para_bot(modo="directo", fecha=fecha, hora="17:00")
    assert res2.exito is True
    assert res2.tipo == "salida"
    assert res2.hora == "17:00"
    # 17:00 - 08:30 = 8.5 horas
    assert res2.datos_jornada["horas_decimal"] == 8.5

    # 3. Completo
    res3 = agente.ejecutar_marcado_para_bot(modo="directo", fecha=fecha, hora="17:30")
    assert res3.exito is False
    assert res3.tipo == "info"


def test_agente_horas_directo_rechaza_si_almuerzo_registrado(
    agente: AgenteAutonomoHoras,
):
    """Verifica que el modo directo rechace la salida si ya se habían registrado marcas de almuerzo."""
    fecha = "2026-11-04"
    agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="08:00")
    agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="12:00")

    # Intentar salida directa teniendo almuerzo
    res_directo = agente.ejecutar_marcado_para_bot(
        modo="directo", fecha=fecha, hora="17:00"
    )
    assert res_directo.exito is False
    assert res_directo.tipo == "error"
    assert "⚠️ Ya hay registros de almuerzo" in res_directo.mensaje


def test_corte_automatico_activa_a_las_17(
    agente: AgenteAutonomoHoras, test_repo: LocalRepository
):
    """Verifica que el corte automático no opere antes de las 17:00 y cierre la jornada a las 17:00."""
    fecha = "2026-11-05"
    agente.ejecutar_marcado_para_bot(modo="directo", fecha=fecha, hora="08:00")

    # A las 16:59 no debe aplicar
    corte_antes = agente.ejecutar_corte_automatico(fecha=fecha, hora_referencia="16:59")
    assert corte_antes is None

    # A las 17:00 o posterior debe aplicar el corte
    corte_ok = agente.ejecutar_corte_automatico(fecha=fecha, hora_referencia="17:00")
    assert isinstance(corte_ok, MarcacionResult)
    assert corte_ok.exito is True
    assert corte_ok.auto_corte is True
    assert corte_ok.tipo == "salida"
    assert corte_ok.hora == "17:00"
    assert corte_ok.datos_jornada["auto_cerrado"] == 1
    assert corte_ok.datos_jornada["hora_salida"] == "17:00"
    # 17:00 - 08:00 = 9.0 horas corridas
    assert corte_ok.datos_jornada["horas_decimal"] == 9.0

    # Segundo intento a las 17:30 no hace nada porque ya está cerrada
    corte_posterior = agente.ejecutar_corte_automatico(
        fecha=fecha, hora_referencia="17:30"
    )
    assert corte_posterior is None


def test_corte_automatico_configuracion_dinamica(
    agente: AgenteAutonomoHoras, test_repo: LocalRepository
):
    """Verifica que el corte respete una HORA_SALIDA_DEFECTO personalizada (ej. 18:00 hs)."""
    test_repo.establecer_configuracion("HORA_SALIDA_DEFECTO", "18:00")
    fecha = "2026-11-06"

    agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="09:00")
    agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="13:00")
    agente.ejecutar_marcado_para_bot(modo="normal", fecha=fecha, hora="14:00")

    # A las 17:30 no corta porque el nuevo límite es 18:00
    assert (
        agente.ejecutar_corte_automatico(fecha=fecha, hora_referencia="17:30") is None
    )

    # A las 18:00 corta
    res = agente.ejecutar_corte_automatico(fecha=fecha, hora_referencia="18:00")
    assert res is not None
    assert res.auto_corte is True
    assert res.hora == "18:00"
    # Horas: (13:00 - 09:00) + (18:00 - 14:00) = 4 + 4 = 8.0 horas
    assert res.datos_jornada["horas_decimal"] == 8.0
    assert res.datos_jornada["auto_cerrado"] == 1


def test_corte_automatico_sin_entrada_o_sin_jornada(agente: AgenteAutonomoHoras):
    """Verifica que el corte automático no haga nada si no hay jornada o no se marcó entrada."""
    assert (
        agente.ejecutar_corte_automatico(fecha="1999-01-01", hora_referencia="19:00")
        is None
    )


def test_formatear_para_telegram_presenter(agente: AgenteAutonomoHoras):
    """Verifica la retrocompatibilidad del método presenter formatear_para_telegram."""
    res_entrada = MarcacionResult(
        exito=True,
        tipo="entrada",
        hora="08:00",
        mensaje="✅ *Entrada* registrado a las 08:00.",
    )
    assert (
        agente.formatear_para_telegram(res_entrada)
        == "✅ *Entrada* registrado a las 08:00."
    )

    res_corte = MarcacionResult(
        exito=True,
        tipo="salida",
        hora="17:00",
        mensaje="",
        auto_corte=True,
    )
    assert (
        agente.formatear_para_telegram(res_corte)
        == "ℹ️ Se aplicó corte automático de jornada a las 17:00 hs."
    )

    # Si se pasa un string plano directamente, debe retornarse intacto
    assert agente.formatear_para_telegram("Texto crudo") == "Texto crudo"


def test_dia_libre_retorna_info_no_registra(agente: AgenteAutonomoHoras):
    """Verifica que si es día libre se retorne MarcacionResult tipo info y no se escriba jornada."""
    with patch.object(agente, "fin_de", return_value=1):
        res = agente.ejecutar_marcado_para_bot(modo="normal", hora="10:00")
        assert res.exito is False
        assert res.tipo == "info"
        assert "día libre" in res.mensaje


def test_calcular_horas_jornada():
    """Verifica los cálculos de horas decimales para distintas combinaciones horarias."""
    calc = AgenteAutonomoHoras.calcular_horas_jornada

    # Sin entrada o sin salida
    assert calc(None, None, None, "17:00") == 0.0
    assert calc("08:00", None, None, None) == 0.0

    # Corrido (directo)
    assert calc("08:00", None, None, "17:00") == 9.0
    assert calc("08:30", None, None, "17:00") == 8.5

    # Con almuerzo
    assert calc("08:00", "12:00", "13:00", "17:00") == 8.0
    assert calc("08:00", "12:30", "13:30", "17:30") == 8.5
    # Ejemplo con minutos parciales (08:00 a 12:15 = 4.25h + 13:15 a 17:00 = 3.75h -> 8.0h)
    assert calc("08:00", "12:15", "13:15", "17:00") == 8.0
