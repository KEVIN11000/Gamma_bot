from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import (
    AbonoRequest,
    CapacidadPagoRequest,
    ObligacionCreate,
    ObligacionUpdate,
    SimulacionRequest,
)
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import safe_int

logger = setup_logger("routes_obligaciones")

obligaciones_bp = Blueprint("obligaciones_v1", __name__)


@obligaciones_bp.route("/obligaciones", methods=["GET"])
@require_api_key
def get_obligaciones() -> Any:
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        raw_obligaciones = repo.get_todas_obligaciones()
        obligaciones = []
        for o in raw_obligaciones:
            obligaciones.append(
                {
                    "id": o.get("ID_Obligacion") or o.get("id", ""),
                    "nombre": o.get("Nombre") or o.get("nombre", ""),
                    "tipo": o.get("Tipo") or o.get("tipo", ""),
                    "entidad": o.get("Entidad") or o.get("entidad", ""),
                    "monto_inicial": safe_int(
                        o.get("Monto_Inicial") or o.get("monto_inicial")
                    ),
                    "saldo_actual": safe_int(
                        o.get("Saldo_Actual") or o.get("saldo_actual")
                    ),
                    "estado": o.get("Estado") or o.get("estado", "Activo"),
                    "cuota_referencia_gs": safe_int(
                        o.get("Cuota_Referencia_Gs") or o.get("Cuotas")
                    ),
                    "cuotas_totales": safe_int(
                        o.get("Cuotas_Totales") or o.get("cuotas_totales", 1)
                    ),
                    "cuotas_restantes": safe_int(
                        o.get("Cuotas_Restantes") or o.get("cuotas_restantes", 1)
                    ),
                    "dia_vencimiento": safe_int(
                        o.get("Dia_Vencimiento") or o.get("dia_vencimiento", 0)
                    ),
                    "fecha_inicio": o.get("Fecha_Inicio") or o.get("fecha_inicio", ""),
                    "observaciones": o.get("Observaciones")
                    or o.get("observaciones", ""),
                }
            )
        return jsonify(obligaciones), 200
    except Exception as e:
        logger.warning(f"Fallback obligaciones: {e}")
        return jsonify([]), 200


@obligaciones_bp.route("/obligaciones", methods=["POST"])
@require_api_key
def create_obligacion() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = ObligacionCreate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from logic.financiero import alta_obligacion

        nueva = alta_obligacion(
            nombre=req_obj.nombre,
            monto_inicial=req_obj.monto_inicial,
            tipo=req_obj.tipo,
            entidad=req_obj.entidad or "General",
            cuotas_totales=req_obj.cuotas_totales or 1,
            cuotas_restantes=req_obj.cuotas_restantes,
            cuota_referencia_gs=req_obj.cuota_referencia_gs,
            saldo_actual=req_obj.saldo_actual,
            estado=req_obj.estado or "Activo",
            fecha_inicio=req_obj.fecha_inicio,
            dia_vencimiento=req_obj.dia_vencimiento or 0,
            observaciones=req_obj.observaciones or "",
            es_gasto_fijo=req_obj.es_gasto_fijo,
        )
        return jsonify(nueva), 201
    except Exception as e:
        logger.warning(f"Error persistiendo obligación: {e}")
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@obligaciones_bp.route("/obligaciones/<obligacion_id>", methods=["PUT"])
@require_api_key
def update_obligacion(obligacion_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = ObligacionUpdate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        existente = repo.get_obligacion_by_id(obligacion_id)
        if not existente:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Obligación {obligacion_id} no encontrada",
                        }
                    }
                ),
                404,
            )

        update_dict: dict[str, Any] = {}
        if req_obj.estado is not None:
            update_dict["Estado"] = req_obj.estado
        if req_obj.saldo_actual is not None:
            update_dict["Saldo_Actual"] = req_obj.saldo_actual
        if req_obj.cuotas_restantes is not None:
            update_dict["Cuotas_Restantes"] = req_obj.cuotas_restantes
        if req_obj.cuotas_totales is not None:
            update_dict["Cuotas_Totales"] = req_obj.cuotas_totales
        if req_obj.cuota_referencia_gs is not None:
            update_dict["Cuota_Referencia_Gs"] = req_obj.cuota_referencia_gs
            update_dict["Cuotas"] = req_obj.cuota_referencia_gs
        if req_obj.dia_vencimiento is not None:
            update_dict["Dia_Vencimiento"] = req_obj.dia_vencimiento
        if req_obj.observaciones is not None:
            update_dict["Observaciones"] = req_obj.observaciones
        if req_obj.nombre is not None:
            update_dict["Nombre"] = req_obj.nombre
        if req_obj.tipo is not None:
            update_dict["Tipo"] = req_obj.tipo
        if req_obj.entidad is not None:
            update_dict["Entidad"] = req_obj.entidad
        if req_obj.es_gasto_fijo is not None:
            update_dict["Es_Gasto_Fijo"] = 1 if req_obj.es_gasto_fijo else 0
        elif req_obj.estado is not None:
            est_lower = req_obj.estado.strip().lower()
            if est_lower in ("pausado", "pausada"):
                update_dict["Es_Gasto_Fijo"] = 0
            elif est_lower in ("activo", "activa"):
                update_dict["Es_Gasto_Fijo"] = 1

        repo.update_obligacion(obligacion_id, update_dict)
        existente.update(update_dict)
        return jsonify(existente), 200
    except Exception as e:
        logger.error(f"Error actualizando obligación {obligacion_id}: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error actualizando obligación: {str(e)}",
                    }
                }
            ),
            500,
        )


@obligaciones_bp.route("/obligaciones/<obligacion_id>", methods=["DELETE"])
@require_api_key
def delete_obligacion(obligacion_id: str) -> Any:
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        existente = repo.get_obligacion_by_id(obligacion_id)
        if not existente:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Obligación {obligacion_id} no encontrada",
                        }
                    }
                ),
                404,
            )

        event_id = existente.get("Event_ID")
        if event_id:
            try:
                from logic.logic import AgenteAutonomoHoras

                spreadsheet_id = (
                    os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
                )
                agente_horas = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
                agente_horas.eliminar_aviso_calendar(event_id)
            except Exception as e_cal:
                logger.warning(f"Error borrando evento Calendar de obligación: {e_cal}")

        repo.delete_obligacion(obligacion_id)
        return jsonify({"status": "deleted", "id": obligacion_id}), 200
    except Exception as e:
        logger.error(f"Error eliminando obligación {obligacion_id}: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error eliminando obligación: {str(e)}",
                    }
                }
            ),
            500,
        )


@obligaciones_bp.route("/obligaciones/abonar", methods=["POST"])
@require_api_key
def abonar_obligacion() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = AbonoRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from logic.financiero import abonar_obligacion as logic_abonar

        res = logic_abonar(
            id_obligacion=req_obj.id_obligacion,
            monto=req_obj.monto,
            nro_factura=getattr(req_obj, "nro_factura", "S/N") or "S/N",
            usar_kwargs_update=True,
        )
        if not res:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Obligación {req_obj.id_obligacion} no encontrada",
                        }
                    }
                ),
                404,
            )
        return jsonify(res), 200
    except Exception as e:
        logger.error(f"Error procesando abono {req_obj.id_obligacion}: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error procesando abono: {str(e)}",
                    }
                }
            ),
            500,
        )


@obligaciones_bp.route("/obligaciones/simular", methods=["POST"])
@require_api_key
def simular_obligacion() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = SimulacionRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    cuota = round(req_obj.monto / req_obj.meses)
    try:
        from logic.financiero import calcular_margen_de_ataque

        margen_actual = calcular_margen_de_ataque()
    except Exception as e_m:
        logger.warning(f"Fallback margen en simulación: {e_m}")
        margen_actual = 2000000

    nuevo_margen = margen_actual - cuota
    diagnostico = (
        "Viable"
        if nuevo_margen > 1000000
        else ("Ajustado" if nuevo_margen > 0 else "Riesgo")
    )
    return (
        jsonify(
            {
                "cuota_mensual": cuota,
                "margen_actual": margen_actual,
                "nuevo_margen": nuevo_margen,
                "diagnostico": diagnostico,
                "detalles": f"Cuota de {cuota:,} ₲ calculada para {req_obj.meses} meses.",
            }
        ),
        200,
    )


@obligaciones_bp.route("/obligaciones/vencimientos", methods=["GET"])
@require_api_key
def get_vencimientos() -> Any:
    try:
        from logic.financiero import obtener_cronograma_vencimientos

        data = obtener_cronograma_vencimientos()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error obteniendo cronograma de vencimientos: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error obteniendo cronograma de vencimientos: {str(e)}",
                    }
                }
            ),
            500,
        )


@obligaciones_bp.route("/obligaciones/foco", methods=["GET"])
@require_api_key
def get_deuda_foco() -> Any:
    criterio = request.args.get("criterio", "prioridad").strip().lower()
    if criterio not in ("prioridad", "saldo"):
        criterio = "prioridad"

    try:
        from logic.financiero import proyectar_cola_deudas

        res = proyectar_cola_deudas(criterio=criterio)
        proyeccion = res.get("proyeccion", [])
        deuda_foco = proyeccion[0] if proyeccion else None

        resp_payload: dict[str, Any] = {
            "criterio": criterio,
            "margen_ataque": res.get("margen_ataque", 0),
            "deuda_foco": deuda_foco,
            "proyeccion": proyeccion,
        }
        # Desempaquetar campos planos de deuda_foco en la raíz para paridad directa con Android DTO
        if isinstance(deuda_foco, dict):
            for k, v in deuda_foco.items():
                if k not in resp_payload:
                    resp_payload[k] = v

        return jsonify(resp_payload), 200
    except Exception as e:
        logger.error(f"Error calculando deuda foco: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error calculando deuda foco: {str(e)}",
                    }
                }
            ),
            500,
        )


@obligaciones_bp.route("/obligaciones/proyectar-capacidad", methods=["POST"])
@require_api_key
def proyectar_capacidad() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = CapacidadPagoRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from logic.financiero import proyectar_capacidad_pago

        resultado = proyectar_capacidad_pago(
            deudas_pausadas_simuladas=req_obj.deudas_pausadas_simuladas,
            abonos_extraordinarios=req_obj.abonos_extraordinarios,
            ajuste_ingreso_extra=req_obj.ajuste_ingreso_extra,
        )
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error proyectando capacidad de pago: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error proyectando capacidad de pago: {str(e)}",
                    }
                }
            ),
            500,
        )
