from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, jsonify

from api.schemas import BootstrapResponse, EstadoJornadaHoyResponse
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("routes_dashboard")

dashboard_bp = Blueprint("dashboard_v1", __name__)

MESES_ES = [
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


def calcular_resumen_financiero() -> dict[str, Any]:
    """Calcula las métricas financieras clave para el dashboard."""
    from logic.financiero import AgenteFinanciero

    spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
    agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
    balance = agente.obtener_balance() if hasattr(agente, "obtener_balance") else {}

    ingresos = balance.get("ingresos", 0)
    gastos = balance.get("gastos", 0)
    flujo_neto = balance.get("flujo_neto", ingresos - gastos)
    saldo_acumulado = balance.get(
        "saldo_acumulado", balance.get("saldo_inicial", 0) + flujo_neto
    )

    # Cálculo de margen libre: presupuesto base (ingresos fijos - gastos fijos) menos cuotas activas fijas
    try:
        from logic.financiero import calcular_margen_de_ataque

        margen_libre = calcular_margen_de_ataque()
    except Exception as e_margen:
        logger.warning(f"Fallback cálculo margen libre: {e_margen}")
        margen_libre = 0

    posicion_iva = balance.get("posicion_iva", 0)
    es_debito_fiscal = balance.get("es_debito_fiscal", False)

    ahora = get_now_py()
    mes_nombre = MESES_ES[ahora.month - 1]
    saldo_inicial = balance.get("saldo_inicial", 0)

    return {
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


@dashboard_bp.route("/dashboard/summary", methods=["GET"])
@require_api_key
def get_dashboard_summary() -> Any:
    try:
        data = calcular_resumen_financiero()
        response = jsonify(data)
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


@dashboard_bp.route("/bootstrap", methods=["GET"])
@require_api_key
def get_bootstrap() -> Any:
    """
    Endpoint unificado de hidratación global atómica para Gamma Mobile.
    Agrupa resumen financiero, estado laboral de hoy, clima, avisos y vencimientos
    con tolerancia estricta a fallos parciales para no bloquear el inicio de la app.
    """
    ahora = get_now_py()

    # 1. Resumen Financiero
    try:
        resumen_financiero = calcular_resumen_financiero()
    except Exception as e_fin:
        logger.warning(f"Error en bootstrap resumen financiero: {e_fin}")
        resumen_financiero = {
            "mes": MESES_ES[ahora.month - 1],
            "saldo_inicial": 0,
            "ingresos": 0,
            "gastos": 0,
            "flujo_neto": 0,
            "margen_libre": 0,
            "saldo_acumulado": 0,
            "posicion_iva": 0,
            "es_debito_fiscal": False,
        }

    # 2. Estado de Asistencia Hoy
    try:
        from api.v1.routes_asistencia import obtener_estado_jornada_hoy_dto

        estado_asistencia = obtener_estado_jornada_hoy_dto()
    except Exception as e_asis:
        logger.warning(f"Error en bootstrap estado asistencia: {e_asis}")
        es_descanso = ahora.weekday() in (5, 6)
        estado_asistencia = EstadoJornadaHoyResponse(
            fecha=ahora.strftime("%d/%m/%Y"),
            estado="LIBRE" if es_descanso else "PENDIENTE",
            hora_entrada=None,
            hora_salida=None,
            minutos_transcurridos=0,
            tiempo_transcurrido_formato="0h 00m",
            puede_marcar_entrada=not es_descanso,
            puede_marcar_salida=False,
            es_feriado_o_descanso=es_descanso,
        )

    # 3. Clima y Alerta de Paraguas
    try:
        from logic.cron_jobs import obtener_datos_clima

        datos_clima = obtener_datos_clima() or {}
        clima_dict = {
            **datos_clima,
            "temperatura": datos_clima.get("temperatura_actual", 0.0),
            "llevar_paraguas": (
                datos_clima.get("alerta_paraguas", {}).get("necesita_paraguas", False)
                if isinstance(datos_clima.get("alerta_paraguas"), dict)
                else False
            ),
            "mensaje": (
                datos_clima.get("alerta_paraguas", {}).get("motivo", "")
                if isinstance(datos_clima.get("alerta_paraguas"), dict)
                else ""
            ),
        }
    except Exception as e_clima:
        logger.warning(f"Error en bootstrap clima: {e_clima}")
        clima_dict = {
            "temperatura": 0.0,
            "temperatura_actual": 0.0,
            "temperatura_min": 0.0,
            "temperatura_max": 0.0,
            "condicion": "No disponible",
            "alerta_paraguas": {
                "necesita_paraguas": False,
                "probabilidad_lluvia": 0,
                "motivo": "No disponible temporalmente",
            },
            "llevar_paraguas": False,
            "mensaje": "Servicio de clima no disponible",
            "actualizado_at": ahora.isoformat(),
        }

    # 4. Próximos Avisos
    try:
        from api.v1.routes_avisos import obtener_lista_avisos_activos

        avisos = obtener_lista_avisos_activos()
    except Exception as e_avisos:
        logger.warning(f"Error en bootstrap avisos: {e_avisos}")
        avisos = []

    # 5. Próximos Vencimientos
    try:
        from logic.financiero import obtener_cronograma_vencimientos

        cronograma = obtener_cronograma_vencimientos()
        vencimientos = (
            cronograma.get("vencimientos", []) if isinstance(cronograma, dict) else []
        )
    except Exception as e_venc:
        logger.warning(f"Error en bootstrap vencimientos: {e_venc}")
        vencimientos = []

    resp_dto = BootstrapResponse(
        resumen_financiero=resumen_financiero,
        estado_asistencia_hoy=estado_asistencia,
        clima=clima_dict,
        proximos_avisos=avisos,
        proximos_vencimientos=vencimientos,
    )
    response = jsonify(resp_dto.model_dump())
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response, 200
