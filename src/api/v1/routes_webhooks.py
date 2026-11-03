from __future__ import annotations

from typing import Any
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import WhatsAppWebhookEvent, WhatsAppWebhookResponse
from api.security import require_webhook_secret, limiter
from app_queue.worker import enqueue
from logger_config import setup_logger

logger = setup_logger("routes_webhooks")

webhooks_bp = Blueprint("webhooks_v1", __name__)


@webhooks_bp.route("/webhooks/whatsapp", methods=["POST"])
@limiter.limit("60 per minute")
@require_webhook_secret
def handle_whatsapp_webhook() -> Any:
    """Ingests incoming WhatsApp events and enqueues messages asynchronously."""
    if request.content_length and request.content_length > 65536:
        return (
            jsonify(
                {
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": "El cuerpo de la petición excede el tamaño máximo permitido (64KB)",
                    }
                }
            ),
            413,
        )
    raw_json = request.get_json(silent=True)
    if not raw_json or not isinstance(raw_json, dict):
        return (
            jsonify(
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Payload JSON inválido o ausente",
                    }
                }
            ),
            400,
        )

    try:
        event = WhatsAppWebhookEvent.model_validate(raw_json)
    except ValidationError as val_err:
        return (
            jsonify(
                {
                    "error": {
                        "code": "UNPROCESSABLE_ENTITY",
                        "message": "Error de validación en el payload del webhook",
                        "details": val_err.errors(),
                    }
                }
            ),
            422,
        )

    # 1. Ignore outgoing messages sent by this instance to avoid feedback loops
    if event.data.from_me:
        logger.info(f"Ignoring outgoing WhatsApp message from {event.data.remote_jid}")
        resp = WhatsAppWebhookResponse(
            status="ignored",
            ignored=True,
            motivo="Mensaje saliente de la propia instancia (from_me=True)",
        )
        return jsonify(resp.model_dump()), 200

    # 2. Check if there is text content to process
    if not event.data.text or not event.data.text.strip():
        logger.info(
            f"Ignoring non-text or empty WhatsApp message from {event.data.remote_jid}"
        )
        resp = WhatsAppWebhookResponse(
            status="ignored",
            ignored=True,
            motivo="Mensaje sin contenido de texto procesable",
        )
        return jsonify(resp.model_dump()), 200

    # 3. Enqueue job into cola.db for asynchronous processing
    try:
        job_id = enqueue(
            recipient_id=event.data.remote_jid,
            operacion="procesar_mensaje_whatsapp",
            payload={
                "remote_jid": event.data.remote_jid,
                "text": event.data.text.strip(),
                "push_name": event.data.push_name,
                "instance": event.instance,
                "event": event.event,
            },
            channel="whatsapp",
        )
        logger.info(f"Enqueued WhatsApp job {job_id} for {event.data.remote_jid}")
        resp = WhatsAppWebhookResponse(
            status="enqueued",
            job_id=job_id,
            ignored=False,
            motivo="Trabajo encolado exitosamente",
        )
        return jsonify(resp.model_dump()), 200

    except Exception as exc:
        logger.error(f"Error encolando evento de WhatsApp: {exc}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "Error interno al encolar el mensaje",
                    }
                }
            ),
            500,
        )
