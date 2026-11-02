from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, jsonify

from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("routes_dashboard")

dashboard_bp = Blueprint("dashboard_v1", __name__)


@dashboard_bp.route("/dashboard/summary", methods=["GET"])
@require_api_key
def get_dashboard_summary() -> Any:
    try:
        from logic.financiero import AgenteFinanciero

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        balance = agente.obtener_balance() if hasattr(agente, "obtener_balance") else {}

        ingresos = balance.get("ingresos", 0)
        gastos = balance.get("gastos", 0)
        flujo_neto = balance.get("flujo_neto", ingresos - gastos)
        saldo_acumulado = balance.get(
            "saldo_acumulado", balance.get("saldo_inicial", 0) + flujo_neto
        )

        # Cálculo de margen libre: presupuesto base (ingresos fijos - gastos fijos) menos cuotas activas
        try:
            from logic.financiero import calcular_margen_de_ataque

            margen_libre = calcular_margen_de_ataque()
        except Exception as e_margen:
            logger.warning(f"Fallback cálculo margen libre: {e_margen}")
            margen_libre = max(0, flujo_neto - int(gastos * 0.2))

        posicion_iva = balance.get("posicion_iva", 0)
        es_debito_fiscal = balance.get("es_debito_fiscal", False)

        ahora = get_now_py()
        meses_es = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Setiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        mes_nombre = meses_es[ahora.month - 1]

        saldo_inicial = balance.get("saldo_inicial", 0)
        response = jsonify(
            {
                "mes": mes_nombre,
                "saldo_inicial": saldo_inicial,
                "ingresos": ingresos,
                "gastos": gastos,
                "flujo_neto": flujo_neto,
                "margen_libre": margen_libre,
                "saldo_acumulado": saldo_acumulado,
                "posicion_iva": posicion_iva,
                "es_debito_fiscal": es_debito_fiscal,
            }
        )
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response, 200
    except Exception as e:
        logger.error(f"Error en /dashboard/summary: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error calculando resumen: {str(e)}",
                    }
                }
            ),
            500,
        )
