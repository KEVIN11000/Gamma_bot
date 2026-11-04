from __future__ import annotations

from typing import Any, Optional
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from adapters.notifications.push_adapter import PushNotificationAdapter
from api.schemas import DispositivoCreate, DispositivoResponse
from api.security import require_api_key
from logger_config import setup_logger

logger = setup_logger("routes_dispositivos")

dispositivos_bp = Blueprint("dispositivos_v1", __name__)

_push_adapter_instance: Optional[PushNotificationAdapter] = None


def get_push_adapter() -> PushNotificationAdapter:
    """Returns or initializes the singleton instance of PushNotificationAdapter."""
    global _push_adapter_instance
    if _push_adapter_instance is None:
        _push_adapter_instance = PushNotificationAdapter()
    return _push_adapter_instance


def set_push_adapter(adapter: Optional[PushNotificationAdapter]) -> None:
    """Sets or resets the PushNotificationAdapter instance (primarily for tests)."""
    global _push_adapter_instance
    _push_adapter_instance = adapter


@dispositivos_bp.route("/dispositivos/registrar", methods=["POST"])
@require_api_key
def registrar_dispositivo() -> Any:
    """Registers or updates a client device token for push notifications."""
    data = request.get_json(silent=True) or {}
    try:
        req = DispositivoCreate(**data)
    except ValidationError as ve:
        return jsonify({"error": "Datos inválidos", "detalles": ve.errors()}), 422

    adapter = get_push_adapter()
    try:
        adapter.registrar_dispositivo(
            device_token=req.device_token,
            platform=req.platform,
            alias_usuario=req.alias_usuario,
        )
        total_activos = adapter.contar_dispositivos(solo_activos=True)
        response = DispositivoResponse(
            status="ok",
            registrado=True,
            dispositivos_activos=total_activos,
        )
        return jsonify(response.model_dump()), 200
    except Exception as exc:
        logger.error(f"Error registrando dispositivo: {exc}")
        return jsonify({"error": f"Error registrando dispositivo: {str(exc)}"}), 500


@dispositivos_bp.route("/dispositivos", methods=["GET"])
@require_api_key
def listar_dispositivos() -> Any:
    """Lists all active registered push devices."""
    adapter = get_push_adapter()
    dispositivos = adapter.listar_dispositivos(solo_activos=True)
    return (
        jsonify(
            {
                "status": "ok",
                "total": len(dispositivos),
                "dispositivos": dispositivos,
            }
        ),
        200,
    )


@dispositivos_bp.route("/dispositivos/notificar", methods=["POST"])
@require_api_key
def notificar_dispositivos() -> Any:
    """Dispatches a push notification to registered devices or a specific token."""
    data = request.get_json(silent=True) or {}
    mensaje = str(data.get("mensaje") or "").strip()
    if not mensaje:
        return jsonify({"error": "El campo 'mensaje' es requerido"}), 422

    recipient = str(data.get("recipient_id") or data.get("device_token") or "broadcast")
    titulo = str(data.get("titulo") or "Gamma Finanzas")
    extra_data = dict(data.get("extra_data") or {})

    adapter = get_push_adapter()
    try:
        enviado = adapter.send_message(
            recipient_id=recipient,
            message=mensaje,
            title=titulo,
            extra_data=extra_data,
        )
        return (
            jsonify(
                {
                    "status": "ok",
                    "enviado": enviado,
                    "destinatario": recipient,
                }
            ),
            200,
        )
    except Exception as exc:
        logger.error(f"Error despachando push desde endpoint: {exc}")
        return jsonify({"error": f"Error despachando notificación: {str(exc)}"}), 500
