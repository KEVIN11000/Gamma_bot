from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request, send_file
from pydantic import ValidationError

from api.schemas import (
    AnaliticasHorasResponse,
    EstadoJornadaHoyResponse,
    PeriodosResponse,
    SyncRequest,
    SyncResponse,
)
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("routes_asistencia")

asistencia_bp = Blueprint("asistencia_v1", __name__)


def _get_reportes_dir() -> Path:
    try:
        import api.blueprint as bp

        return bp.REPORTES_DIR
    except Exception:
        return Path(__file__).resolve().parents[2] / "reportes"


def obtener_estado_jornada_hoy_dto() -> EstadoJornadaHoyResponse:
    """Calcula y retorna el DTO del estado de la jornada laboral de hoy."""
    from repositories.local_repository import get_local_repository

    repo = get_local_repository()
    ahora = get_now_py()
    fecha_iso = ahora.strftime("%Y-%m-%d")
    fecha_display = ahora.strftime("%d/%m/%Y")
    es_descanso = ahora.weekday() in (5, 6)

    jornada = repo.obtener_jornada_por_fecha(fecha_iso)

    if not jornada or not jornada.get("hora_entrada"):
        estado = "LIBRE" if es_descanso else "PENDIENTE"
        return EstadoJornadaHoyResponse(
            fecha=fecha_display,
            estado=estado,
            hora_entrada=None,
            hora_salida=None,
            minutos_transcurridos=0,
            tiempo_transcurrido_formato="0h 00m",
            puede_marcar_entrada=not es_descanso,
            puede_marcar_salida=False,
            es_feriado_o_descanso=es_descanso,
        )

    h_in = str(jornada.get("hora_entrada", "")).strip()
    h_out = jornada.get("hora_salida")
    if h_out:
        h_out = str(h_out).strip()

    if not h_out:
        minutos = 0
        try:
            dt_in = datetime.strptime(f"{fecha_iso} {h_in}", "%Y-%m-%d %H:%M")
            dt_in = dt_in.replace(tzinfo=ahora.tzinfo)
            minutos = max(0, int((ahora - dt_in).total_seconds() // 60))
        except Exception:
            pass

        horas = minutos // 60
        mins = minutos % 60
        tiempo_fmt = f"{horas}h {mins:02d}m"

        return EstadoJornadaHoyResponse(
            fecha=fecha_display,
            estado="TRABAJANDO",
            hora_entrada=h_in,
            hora_salida=None,
            minutos_transcurridos=minutos,
            tiempo_transcurrido_formato=tiempo_fmt,
            puede_marcar_entrada=False,
            puede_marcar_salida=True,
            es_feriado_o_descanso=es_descanso,
        )

    horas_dec = float(jornada.get("horas_decimal", 0.0) or 0.0)
    minutos_totales = int(round(horas_dec * 60))
    horas = minutos_totales // 60
    mins = minutos_totales % 60
    tiempo_fmt = f"{horas}h {mins:02d}m"

    return EstadoJornadaHoyResponse(
        fecha=fecha_display,
        estado="COMPLETADO",
        hora_entrada=h_in,
        hora_salida=h_out,
        minutos_transcurridos=minutos_totales,
        tiempo_transcurrido_formato=tiempo_fmt,
        puede_marcar_entrada=False,
        puede_marcar_salida=False,
        es_feriado_o_descanso=es_descanso,
    )


@asistencia_bp.route("/asistencia/estado-hoy", methods=["GET"])
@require_api_key
def get_estado_jornada_hoy() -> Any:
    """Consulta el estado del reloj y jornada laboral de hoy sin mutar datos."""
    try:
        resp = obtener_estado_jornada_hoy_dto()
        return jsonify(resp.model_dump()), 200
    except Exception as exc:
        logger.error(f"Error consultando estado de jornada hoy: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "INTERNAL_ERROR",
                    "mensaje": f"No se pudo consultar la jornada actual: {exc}",
                }
            ),
            500,
        )


@asistencia_bp.route("/asistencia/marcar", methods=["POST"])
@require_api_key
def marcar_asistencia() -> Any:
    data = request.get_json(silent=True) or {}
    modo = data.get("modo", "normal")
    if modo not in ("normal", "directo"):
        modo = "normal"

    spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
    if not spreadsheet_id:
        return (
            jsonify(
                {
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "SPREADSHEET_ID no configurado",
                    }
                }
            ),
            500,
        )

    try:
        from logic.logic import AgenteAutonomoHoras

        agente = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
        resultado = agente.ejecutar_marcado_para_bot(modo=modo)

        # Consumo directo de DTO MarcacionResult puro
        if hasattr(resultado, "tipo") and hasattr(resultado, "mensaje"):
            if resultado.tipo == "error":
                status_code = 409 if "⚠️" in resultado.mensaje else 400
                return (
                    jsonify({"tipo": "error", "mensaje": resultado.mensaje}),
                    status_code,
                )
            elif resultado.tipo == "info":
                return (
                    jsonify(
                        {
                            "status": "ok",
                            "tipo": "info",
                            "mensaje": resultado.mensaje,
                            "confirmado_en_planilla": True,
                        }
                    ),
                    200,
                )
            else:
                return (
                    jsonify(
                        {
                            "tipo": resultado.tipo,
                            "hora": resultado.hora,
                            "mensaje": resultado.mensaje,
                            "auto_corte": getattr(resultado, "auto_corte", False),
                            "datos_jornada": getattr(resultado, "datos_jornada", {}),
                        }
                    ),
                    200,
                )

        # Fallback de compatibilidad si mocks en tests devuelven string plano
        res_str = str(resultado)
        if res_str.startswith("❌"):
            return jsonify({"tipo": "error", "mensaje": res_str}), 400
        elif res_str.startswith("⚠️"):
            return jsonify({"tipo": "error", "mensaje": res_str}), 409
        elif res_str.startswith("ℹ️"):
            return (
                jsonify(
                    {
                        "status": "ok",
                        "tipo": "info",
                        "mensaje": res_str,
                        "confirmado_en_planilla": True,
                    }
                ),
                200,
            )

        tipo = "salida" if "salida" in res_str.lower() else "entrada"
        match_hora = re.search(r"\b(\d{2}:\d{2})\b", res_str)
        hora = match_hora.group(1) if match_hora else get_now_py().strftime("%H:%M")

        return (
            jsonify(
                {
                    "tipo": tipo,
                    "hora": hora,
                    "mensaje": res_str,
                }
            ),
            200,
        )
    except Exception as e:
        resp_status = getattr(getattr(e, "response", None), "status_code", None)
        if resp_status == 429 or "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            logger.warning(
                f"Google Sheets rate limit excedido en marcar_asistencia: {e}"
            )
            return (
                jsonify(
                    {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Servicio de Google Sheets saturado temporalmente. "
                                "Espera 60 segundos antes de reintentar."
                            ),
                        }
                    }
                ),
                429,
            )
        logger.error(f"Error en marcación de asistencia: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "SERVICE_ERROR",
                        "message": f"Error conectando con planilla de asistencia: {str(e)}",
                    }
                }
            ),
            502,
        )


@asistencia_bp.route("/asistencia/materias", methods=["GET"])
@require_api_key
def get_materias() -> Any:
    materias: list[str] = []
    try:
        from logic.logic import AgenteAsistenciaMaterias

        agente = AgenteAsistenciaMaterias()
        horarios = agente.HORARIOS_MATERIAS
        if horarios:
            materias = sorted(list(horarios.keys()))
    except Exception as e:
        logger.warning(f"Error cargando materias desde Config_bot: {e}")

    # Fallback si Config_bot no está accesible en entorno dev
    if not materias:
        materias = [
            "Algoritmos y Estructuras de Datos",
            "Base de Datos",
            "Inteligencia Artificial",
            "Ingeniería de Software",
            "Sistemas Operativos",
            "Redes de Computadoras",
            "Programación Web",
            "Matemática Discreta",
            "Física",
            "Cálculo",
        ]
    return jsonify(materias), 200


@asistencia_bp.route("/asistencia/materia", methods=["POST"])
@require_api_key
def marcar_materia() -> Any:
    data = request.get_json(silent=True) or {}
    materia_solicitada = (data.get("materia") or "").strip()
    ahora = get_now_py()

    try:
        from logic.logic import AgenteAsistenciaMaterias

        agente = AgenteAsistenciaMaterias()
        horarios = agente.HORARIOS_MATERIAS

        # 1. Validar si los horarios de materias están disponibles
        if horarios is None:
            logger.warning("No se pudieron cargar los horarios de Config_bot.")
            msg = "⚠️ No se pudo verificar el horario oficial de materias en el servidor (servicio no disponible)."
            return (
                jsonify(
                    {
                        "error": {
                            "code": "SERVICE_UNAVAILABLE",
                            "message": msg,
                        },
                        "mensaje": msg,
                    }
                ),
                503,
            )

        # 2. Verificar si hay clase en curso actualmente
        materia_en_curso, tipo = agente.obtener_materia_actual(ahora)
        if not materia_en_curso:
            msg = (
                f"ℹ️ No hay clase en curso para '{materia_solicitada}' en este momento según el horario oficial."
                if materia_solicitada
                else "ℹ️ No hay ninguna clase en curso en este momento según el horario oficial."
            )
            return (
                jsonify(
                    {
                        "error": {"code": "NO_CLASE_EN_CURSO", "message": msg},
                        "mensaje": msg,
                    }
                ),
                400,
            )

        # 3. Si el usuario seleccionó una materia específica, validar que coincida con la que está en curso
        if (
            materia_solicitada
            and materia_solicitada.lower() != "general"
            and materia_solicitada.lower() != materia_en_curso.lower()
        ):
            msg = f"ℹ️ La clase en curso es '{materia_en_curso}', no '{materia_solicitada}'."
            return (
                jsonify(
                    {
                        "error": {"code": "MATERIA_MISMATCH", "message": msg},
                        "mensaje": msg,
                    }
                ),
                400,
            )

        # 4. Registrar la asistencia real en Google Sheets
        resultado = agente.marcar_asistencia()
        if resultado.startswith("❌"):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "ASISTENCIA_ERROR",
                            "message": resultado,
                        },
                        "mensaje": resultado,
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "materia": materia_en_curso,
                    "hora": ahora.strftime("%H:%M"),
                    "mensaje": resultado,
                }
            ),
            200,
        )

    except Exception as e:
        resp_status = getattr(getattr(e, "response", None), "status_code", None)
        if resp_status == 429 or "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            logger.warning(f"Google Sheets rate limit excedido en marcar_materia: {e}")
            return (
                jsonify(
                    {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Servicio de Google Sheets saturado temporalmente. "
                                "Espera 60 segundos antes de reintentar."
                            ),
                        }
                    }
                ),
                429,
            )
        logger.error(f"Error procesando marcación de materia: {e}")
        msg = f"❌ Error interno al registrar materia: {str(e)}"
        return (
            jsonify(
                {
                    "error": {"code": "INTERNAL_ERROR", "message": msg},
                    "mensaje": msg,
                }
            ),
            500,
        )


@asistencia_bp.route("/asistencia/periodos", methods=["GET"])
@require_api_key
def get_asistencia_periodos() -> Any:
    """Retorna el estado de períodos laboral y contable, indicando si están sincronizados."""
    try:
        from logic.logic import obtener_estado_periodos

        estado = obtener_estado_periodos()
        dto = PeriodosResponse(**estado)
        return jsonify(dto.model_dump()), 200
    except Exception as e:
        logger.error(f"Error obteniendo períodos de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@asistencia_bp.route("/asistencia/analiticas", methods=["GET"])
@require_api_key
def get_asistencia_analiticas() -> Any:
    """Retorna analíticas laborales MTD: horas perdidas, horas extras, balance neto y acumulado."""
    try:
        hoja = request.args.get("hoja")
        from logic.logic import AgenteAutonomoHoras

        agente = AgenteAutonomoHoras()
        analiticas, error = agente.calcular_analiticas_asistencia(nombre_hoja=hoja)
        if error:
            return (
                jsonify({"error": {"code": "ANALITICAS_ERROR", "message": str(error)}}),
                400,
            )

        dto = AnaliticasHorasResponse(**analiticas)
        return jsonify(dto.model_dump()), 200
    except Exception as e:
        logger.error(f"Error calculando analíticas de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@asistencia_bp.route("/asistencia/reporte/excel", methods=["GET"])
@require_api_key
def descargar_reporte_excel() -> Any:
    """Genera y descarga la planilla nativa Excel (.xlsx) con el formato oficial."""
    try:
        hoja = request.args.get("hoja")
        descuento = float(request.args.get("descuento", 0) or 0)
        saldo_anterior = float(request.args.get("saldo_anterior", 0) or 0)
        incluir_iva = request.args.get("incluir_iva", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        from logic.logic import AgenteAutonomoHoras
        from services.excel_service import ExcelReportService

        agente = AgenteAutonomoHoras()
        datos, error = agente.preparar_datos_reporte(
            nombre_hoja=hoja,
            descuento=descuento,
            saldo_anterior=saldo_anterior,
            incluir_iva=incluir_iva,
        )
        if error:
            return (
                jsonify({"error": {"code": "REPORTE_ERROR", "message": str(error)}}),
                400,
            )

        reportes_dir = _get_reportes_dir()
        excel_service = ExcelReportService(output_dir=reportes_dir)
        ruta_archivo = excel_service.generar_reporte_horas(datos)

        return send_file(
            ruta_archivo,
            mimetype=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            as_attachment=True,
            download_name=os.path.basename(ruta_archivo),
        )
    except Exception as e:
        logger.error(f"Error generando reporte Excel de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@asistencia_bp.route("/asistencia/reporte/pdf", methods=["GET"])
@require_api_key
def descargar_reporte_pdf_asistencia() -> Any:
    """Genera y descarga el reporte PDF de horas con cuadro resumen oficial."""
    try:
        hoja = request.args.get("hoja")
        descuento = float(request.args.get("descuento", 0) or 0)
        saldo_anterior = float(request.args.get("saldo_anterior", 0) or 0)
        incluir_iva = request.args.get("incluir_iva", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        from logic.logic import AgenteAutonomoHoras
        from logic.pdf_service import PDFService

        agente = AgenteAutonomoHoras()
        datos, error = agente.preparar_datos_reporte(
            nombre_hoja=hoja,
            descuento=descuento,
            saldo_anterior=saldo_anterior,
            incluir_iva=incluir_iva,
        )
        if error:
            return (
                jsonify({"error": {"code": "REPORTE_ERROR", "message": str(error)}}),
                400,
            )

        pdf_service = PDFService()
        ruta_archivo = pdf_service.generar_reporte_generico(datos)

        return send_file(
            ruta_archivo,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=os.path.basename(ruta_archivo),
        )
    except Exception as e:
        logger.error(f"Error generando reporte PDF de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@asistencia_bp.route("/asistencia/sync", methods=["POST"])
@require_api_key
def sincronizar_asistencia() -> Any:
    """
    Sincroniza bidireccionalmente los registros de asistencia entre SQLite local y Google Sheets.
    """
    data = request.get_json(silent=True) or {}
    try:
        req_obj = SyncRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from services.sync_service import SyncService

        service = SyncService(spreadsheet_id=os.getenv("SPREADSHEET_ID"))
        if req_obj.direccion == "local_to_sheets":
            resultado = service.volcar_local_a_sheets(
                mes=req_obj.mes, anio=req_obj.anio, modulo=req_obj.modulo
            )
        else:
            resultado = service.volcar_sheets_a_local(
                mes=req_obj.mes, anio=req_obj.anio, modulo=req_obj.modulo
            )

        resp_dto = SyncResponse(**resultado)
        status_code = 200 if resp_dto.exito else 502
        return jsonify(resp_dto.model_dump()), status_code
    except Exception as e:
        logger.error(f"Error en sincronización de asistencia: {e}")
        return (
            jsonify(
                {
                    "exito": False,
                    "registros_sincronizados": 0,
                    "detalles": f"Error interno en servicio de sincronización: {str(e)}",
                }
            ),
            500,
        )
