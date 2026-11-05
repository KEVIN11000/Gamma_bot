from __future__ import annotations

import uuid
from typing import Any
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import (
    ProyectoSimularRequest,
    ProyectoSimularResponse,
    ProyectoAprobarResponse,
)
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py, safe_int

logger = setup_logger("routes_proyectos")

proyectos_bp = Blueprint("proyectos_v1", __name__)


@proyectos_bp.route("/proyectos/simular", methods=["POST"])
@require_api_key
def simular_proyecto() -> Any:
    """Evalúa la viabilidad de un proyecto o inversión y lo registra en estado 'Simulado'."""
    payload = request.get_json(silent=True) or {}
    try:
        req = ProyectoSimularRequest(**payload)
    except ValidationError as ve:
        return (
            jsonify(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "mensaje": "Datos de simulación inválidos.",
                    "detalles": ve.errors(),
                }
            ),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        ingreso_base, gf = repo.obtener_presupuesto_base_completo()

        # Si no hay ingreso base configurado, intentar promedio de ingresos históricos
        if ingreso_base <= 0:
            movimientos = repo.get_all_movimientos()
            meses_activos: set[str] = set()
            total_ingresos_historicos = 0

            for m in movimientos:
                tipo = str(m.get("Movimiento", m.get("Tipo", ""))).strip().lower()
                if tipo == "ingreso":
                    monto_mov = safe_int(m.get("Total", m.get("Monto", 0)))
                    fecha = str(m.get("Fecha", "")).strip()
                    mes_str = fecha[:7] if len(fecha) >= 7 else "desc"
                    meses_activos.add(mes_str)
                    total_ingresos_historicos += monto_mov

            if meses_activos:
                ingreso_base = total_ingresos_historicos // len(meses_activos)
            else:
                ingreso_base = 1

        deudas_activas = repo.get_obligaciones_activas()
        qd_act = 0
        for d in deudas_activas:
            estado = str(d.get("Estado", "")).strip().lower()
            if estado in ("pausado", "pausada", "cancelado", "pagado", "inactivo"):
                continue

            raw_fijo = str(d.get("Es_Gasto_Fijo", "1")).strip().lower()
            es_fijo = (
                raw_fijo in ("1", "true", "si", "yes", "t") if raw_fijo != "" else True
            )
            if not es_fijo:
                continue

            cuota_ref = safe_int(d.get("Cuota_Referencia_Gs", 0))
            if cuota_ref > 0:
                qd_act += cuota_ref
            else:
                m_total = safe_int(d.get("Monto_Inicial", 0))
                cuotas = safe_int(d.get("Cuotas", d.get("Cuotas_Totales", 1)))
                if cuotas <= 0:
                    cuotas = 1
                qd_act += m_total // cuotas

        cuota_mensual = req.monto // req.meses if req.meses > 0 else req.monto
        mld = ingreso_base - gf - qd_act - cuota_mensual
        dti = (
            ((qd_act + cuota_mensual) / ingreso_base) * 100
            if ingreso_base > 0
            else 100.0
        )

        if dti <= 30 and mld > 0:
            diagnostico = "Viable"
            semaforo = "VERDE"
            mensaje = "Tu salud financiera soporta esta nueva cuota cómodamente."
        elif dti <= 40 and mld > 0:
            diagnostico = "Ajustado"
            semaforo = "AMARILLO"
            mensaje = "Puedes pagarlo, pero tu presupuesto quedará muy ajustado para emergencias."
        else:
            diagnostico = "Riesgo"
            semaforo = "ROJO"
            mensaje = "Operación de Alto Riesgo. La cuota supera tu capacidad de pago o te deja en saldo rojo."

        id_proyecto = f"PRY-{uuid.uuid4().hex[:6].upper()}"
        fecha_str = get_now_py().strftime("%d/%m/%Y")

        obligacion_dict = {
            "ID_Obligacion": id_proyecto,
            "Tipo": "Proyecto",
            "Nombre": req.concepto.strip(),
            "Entidad": "Proyecto",
            "Monto_Inicial": req.monto,
            "Saldo_Actual": req.monto,
            "Estado": "Simulado",
            "Cuota_Referencia_Gs": cuota_mensual,
            "Fecha_Inicio": "",
            "Observaciones": f"Simulado vía API el {fecha_str}",
            "Cuotas": req.meses,
            "Event_ID": "",
            "Dia_Vencimiento": 0,
            "Cuotas_Totales": req.meses,
            "Cuotas_Restantes": req.meses,
            "Orden_Prioridad": 999,
            "Es_Gasto_Fijo": 0,
        }
        repo.insert_obligacion(obligacion_dict)

        resp_obj = ProyectoSimularResponse(
            id_proyecto=id_proyecto,
            concepto=req.concepto.strip(),
            monto_total=req.monto,
            meses=req.meses,
            cuota_mensual=cuota_mensual,
            ingreso_base=int(ingreso_base),
            gastos_fijos=int(gf),
            cuotas_actuales=int(qd_act),
            margen_libre_post_proyecto=int(mld),
            dti_resultante=round(float(dti), 1),
            diagnostico=diagnostico,
            semaforo=semaforo,
            mensaje=mensaje,
        )
        return jsonify(resp_obj.model_dump()), 200
    except Exception as exc:
        logger.error(f"Error simulando proyecto: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "INTERNAL_ERROR",
                    "mensaje": f"No se pudo simular el proyecto: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )


@proyectos_bp.route("/proyectos/<id_proyecto>/aprobar", methods=["POST"])
@require_api_key
def aprobar_proyecto(id_proyecto: str) -> Any:
    """Aprueba un proyecto previamente simulado, activándolo en Obligaciones_Maestro."""
    id_limpio = id_proyecto.strip()
    if not id_limpio:
        return (
            jsonify(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "mensaje": "El ID de proyecto no puede estar vacío.",
                    "detalles": None,
                }
            ),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        obligacion = repo.get_obligacion_by_id(id_limpio)

        if not obligacion:
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "NOT_FOUND",
                        "mensaje": f"No se encontró ningún proyecto con ID '{id_limpio}'.",
                        "detalles": None,
                    }
                ),
                404,
            )

        estado_actual = str(obligacion.get("Estado", "")).strip().lower()
        if estado_actual in ("activo", "activa"):
            return (
                jsonify(
                    {
                        "status": "ok",
                        "id_proyecto": id_limpio,
                        "estado": "Activo",
                        "mensaje": "El proyecto ya se encontraba activo.",
                    }
                ),
                200,
            )

        repo.update_obligacion_estado(id_limpio, "Activo")

        resp_obj = ProyectoAprobarResponse(
            status="ok",
            id_proyecto=id_limpio,
            estado="Activo",
            mensaje="Proyecto aprobado e incorporado como obligación activa.",
        )
        return jsonify(resp_obj.model_dump()), 200
    except Exception as exc:
        logger.error(f"Error aprobando proyecto '{id_limpio}': {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "SHEETS_ERROR",
                    "mensaje": f"Error al actualizar estado en Google Sheets: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )
