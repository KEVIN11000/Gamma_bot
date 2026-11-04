from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Tuple

from logger_config import setup_logger

logger = setup_logger("presupuesto_service")

# Almacén en memoria para control de cooldown: (recipient_id, categoria_lower) -> timestamp_unix
_COOLDOWN_ALERTAS: Dict[Tuple[str, str], float] = {}
COOLDOWN_SEGUNDOS_DEFAULT: float = 86400.0  # 24 horas


def get_cooldown_store() -> Dict[Tuple[str, str], float]:
    """Retorna el almacén de marcas de tiempo de alertas."""
    return _COOLDOWN_ALERTAS


def reset_presupuesto_cooldown() -> None:
    """Limpia el almacén de cooldown (útil para pruebas y reinicio diario)."""
    _COOLDOWN_ALERTAS.clear()


def formatear_monto_gs(monto: float | int) -> str:
    """Formatea un monto numérico con separador de miles paraguayo."""
    return f"{int(monto):,}".replace(",", ".") + " Gs"


def despachar_alerta_presupuestaria_proactiva(
    categoria: str,
    monto_nuevo: float = 0.0,
    recipient_id: Optional[str] = None,
    channel: str = "telegram",
    local_repo: Any = None,
    sheets_repo: Any = None,
    custom_now: Optional[float] = None,
    cooldown_segundos: float = COOLDOWN_SEGUNDOS_DEFAULT,
) -> Dict[str, Any]:
    """Evalúa el techo presupuestario y emite una alerta proactiva multi-canal si supera el umbral.

    Aplica un cooldown de 24 horas por categoría y destinatario para no saturar al usuario
    con múltiples advertencias repetitivas en el mismo día.

    Args:
        categoria: Categoría del egreso (ej: 'Comida', 'Combustible', 'Supermercado').
        monto_nuevo: Monto recién registrado a evaluar.
        recipient_id: Destinatario (Chat ID de Telegram o número WhatsApp). Si es None, usa CHAT_ID.
        channel: Canal de entrega ('telegram', 'whatsapp').
        local_repo: Instancia opcional de LocalRepository para pruebas.
        sheets_repo: Instancia opcional de SheetsRepository para pruebas.
        custom_now: Marca de tiempo unix opcional para testing determinista de cooldown.
        cooldown_segundos: Período de enfriamiento en segundos (default: 86400 = 24h).

    Returns:
        Diccionario con el resultado de la evaluación y estado del despacho.
    """
    cat_limpia = categoria.strip()
    if not cat_limpia:
        return {"emitida": False, "motivo": "categoria_vacia"}

    # Resolver destinatario por defecto si no fue provisto
    target_recipient = str(recipient_id or os.getenv("CHAT_ID") or "default_recipient")

    try:
        from logic.financiero import evaluar_techo_presupuestario

        alerta = evaluar_techo_presupuestario(
            categoria=cat_limpia,
            monto_nuevo=monto_nuevo,
            local_repo=local_repo,
            sheets_repo=sheets_repo,
        )
    except Exception as exc:
        logger.warning(
            f"Error evaluando techo presupuestario para '{cat_limpia}': {exc}"
        )
        return {"emitida": False, "motivo": f"error_evaluacion: {exc}"}

    # Si las alertas están inactivas o no superó el umbral
    if not alerta.get("activo") or not alerta.get("alerta_emitida"):
        return {
            "emitida": False,
            "motivo": "dentro_de_limite",
            "alerta": alerta,
        }

    # Verificar período de cooldown
    now_ts = custom_now if custom_now is not None else time.time()
    clave_cooldown = (target_recipient, cat_limpia.lower())
    ultimo_envio = _COOLDOWN_ALERTAS.get(clave_cooldown, 0.0)

    if now_ts - ultimo_envio < cooldown_segundos:
        logger.info(
            f"Alerta presupuestaria para '{cat_limpia}' suprimida por cooldown "
            f"(hace {int(now_ts - ultimo_envio)}s < {int(cooldown_segundos)}s)"
        )
        return {
            "emitida": False,
            "motivo": "cooldown_activo",
            "segundos_restantes": round(cooldown_segundos - (now_ts - ultimo_envio), 1),
            "alerta": alerta,
        }

    # Construir mensaje enriquecido con emojis
    porcentaje = alerta.get("porcentaje_consumido", 0.0)
    gastado = alerta.get("monto_gastado", 0)
    limite = alerta.get("limite_presupuesto", 0)
    restante = max(0, limite - gastado)

    mensaje_alerta = (
        f"⚠️ *Alerta Presupuestaria: {cat_limpia}*\n\n"
        f"Has alcanzado el *{porcentaje:.1f}%* de tu presupuesto mensual para esta categoría.\n"
        f"📊 *Consumo:* {formatear_monto_gs(gastado)} de {formatear_monto_gs(limite)}\n"
        f"💡 *Disponible restante:* {formatear_monto_gs(restante)}"
    )

    # Encolar notificación asíncrona en cola.db
    job_id = None
    try:
        from app_queue.worker import enqueue

        job_id = enqueue(
            recipient_id=target_recipient,
            operacion="enviar_notificacion",
            payload={"mensaje": mensaje_alerta},
            channel=channel,
        )
        # Actualizar timestamp de cooldown tras encolar con éxito
        _COOLDOWN_ALERTAS[clave_cooldown] = now_ts
        logger.info(
            f"Alerta presupuestaria encolada job_id={job_id} para {target_recipient} ({cat_limpia})"
        )
    except Exception as exc_enqueue:
        logger.error(f"Error encolando alerta presupuestaria: {exc_enqueue}")
        return {
            "emitida": False,
            "motivo": f"error_encolado: {exc_enqueue}",
            "alerta": alerta,
        }

    return {
        "emitida": True,
        "job_id": job_id,
        "mensaje": mensaje_alerta,
        "alerta": alerta,
    }
