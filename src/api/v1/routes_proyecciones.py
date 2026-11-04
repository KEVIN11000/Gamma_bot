from __future__ import annotations

import os
from typing import Any
from flask import Blueprint, jsonify, request

from api.schemas import FlujoCajaResponse
from api.security import require_api_key
from logger_config import setup_logger
from services.cashflow_service import CashFlowProjector

logger = setup_logger("routes_proyecciones")

proyecciones_bp = Blueprint("proyecciones_v1", __name__)


@proyecciones_bp.route("/proyecciones/flujo-caja", methods=["GET"])
@require_api_key
def get_proyeccion_flujo_caja() -> Any:
    """Calcula y retorna la serie de flujo de caja proyectada a 30 días para Gamma Mobile."""
    try:
        saldo_param = request.args.get("saldo_inicial")
        gasto_diario_param = request.args.get("gasto_diario")
        reserva_param = request.args.get("umbral_reserva")

        saldo_inicial: float = 0.0
        if saldo_param is not None:
            try:
                saldo_inicial = float(saldo_param)
            except ValueError:
                saldo_inicial = 0.0
        else:
            try:
                from logic.financiero import AgenteFinanciero

                sheet_id = (
                    os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
                )
                agente = AgenteFinanciero(spreadsheet_id=sheet_id)
                bal = (
                    agente.obtener_balance()
                    if hasattr(agente, "obtener_balance")
                    else {}
                )
                saldo_inicial = float(
                    bal.get(
                        "saldo_acumulado",
                        bal.get("saldo_inicial", 0)
                        + (bal.get("ingresos", 0) - bal.get("gastos", 0)),
                    )
                )
            except Exception as e_bal:
                logger.debug(f"Fallback saldo inicial a 0.0: {e_bal}")
                saldo_inicial = 0.0

        gasto_diario = float(gasto_diario_param) if gasto_diario_param else 0.0
        umbral_reserva = float(reserva_param) if reserva_param else 0.0

        projector = CashFlowProjector()
        resultado = projector.proyectar_30_dias(
            saldo_inicial=saldo_inicial,
            gasto_diario_estimado=gasto_diario,
            umbral_reserva_minima=umbral_reserva,
        )

        resp_obj = FlujoCajaResponse(**resultado.to_dict())
        response = jsonify(resp_obj.model_dump())
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        return response, 200

    except Exception as exc:
        logger.error(f"Error calculando proyección de flujo de caja: {exc}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "PROJECTION_ERROR",
                        "message": f"Error calculando proyección: {exc}",
                    }
                }
            ),
            500,
        )
