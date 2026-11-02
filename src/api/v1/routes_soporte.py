from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import TicketCreate, TicketUpdate
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("routes_soporte")

soporte_bp = Blueprint("soporte_v1", __name__)


def _get_tickets_file() -> Path:
    try:
        import api.blueprint as bp

        return bp.TICKETS_FILE
    except Exception:
        return Path(__file__).resolve().parents[2] / "data" / "tickets.json"


def _get_base_dir() -> Path:
    try:
        import api.blueprint as bp

        return bp.BASE_DIR
    except Exception:
        return Path(__file__).resolve().parents[2]


@soporte_bp.route("/soporte/tickets", methods=["GET"])
@require_api_key
def get_tickets() -> Any:
    tickets_file = _get_tickets_file()
    if tickets_file.exists():
        try:
            with open(tickets_file, "r", encoding="utf-8") as f:
                tickets = json.load(f)
            # Asegurar retrocompatibilidad para registros que no tengan origen o resolución
            for t in tickets:
                if "origen" not in t:
                    t["origen"] = "app"
                if "resolucion" not in t:
                    t["resolucion"] = None
            return jsonify(tickets), 200
        except Exception:
            pass
    return jsonify([]), 200


@soporte_bp.route("/soporte/tickets", methods=["POST"])
@require_api_key
def create_ticket() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = TicketCreate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    tickets_file = _get_tickets_file()
    tickets = []
    if tickets_file.exists():
        try:
            with open(tickets_file, "r", encoding="utf-8") as f:
                tickets = json.load(f)
        except Exception:
            tickets = []

    nuevo_ticket = {
        "id": f"TCK-{len(tickets) + 1:03d}",
        "asunto": req_obj.asunto,
        "descripcion": req_obj.descripcion or "",
        "estado": "Abierto",
        "fecha": get_now_py().strftime("%d/%m/%Y"),
        "origen": req_obj.origen or "app",
        "resolucion": None,
    }
    tickets.insert(0, nuevo_ticket)
    try:
        with open(tickets_file, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando ticket: {e}")

    # Telemetría Vigía (creación de Issue en GitHub)
    try:
        from com.core.telemetry import reportar_incidente_vigia

        reportar_incidente_vigia(
            titulo=f"[APP TICKET] {nuevo_ticket['id']}: {req_obj.asunto}",
            detalle=(
                f"Ticket reportado desde Gamma Mobile:\n\n"
                f"{req_obj.descripcion or 'Sin detalle'}"
            ),
            origen="gamma-mobile",
        )
    except Exception as e_vigia:
        logger.warning(f"No se pudo reportar a Vigía: {e_vigia}")

    # Alerta push al Telegram del Administrador
    try:
        chat_id = os.getenv("CHAT_ID")
        if chat_id:
            from flask_app import bot_instance

            if bot_instance and hasattr(bot_instance, "bot") and bot_instance.bot:
                bot_instance.bot.send_message(
                    int(chat_id),
                    f"🎫 <b>Nuevo Ticket de Soporte (App Móvil)</b>\n\n"
                    f"🆔 <b>ID:</b> <code>{nuevo_ticket['id']}</code>\n"
                    f"📌 <b>Asunto:</b> {nuevo_ticket['asunto']}\n"
                    f"📝 <b>Descripción:</b> {nuevo_ticket['descripcion']}\n"
                    f"📅 <b>Fecha:</b> {nuevo_ticket['fecha']}\n"
                    f"🌐 <b>Origen:</b> {nuevo_ticket['origen']}",
                    parse_mode="HTML",
                )
    except Exception as e_tg:
        logger.warning(f"No se pudo enviar notificación de ticket a Telegram: {e_tg}")

    # Sincronización con GitHub Issues si GITHUB_TOKEN está configurado
    try:
        from services.github_service import GitHubIssueSyncService

        GitHubIssueSyncService.create_github_issue(nuevo_ticket)
    except Exception as e_gh:
        logger.warning(f"Error no bloqueante al crear issue en GitHub: {e_gh}")

    return jsonify(nuevo_ticket), 201


@soporte_bp.route("/soporte/tickets/<ticket_id>", methods=["PATCH"])
@require_api_key
def update_ticket(ticket_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = TicketUpdate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    estados_validos = {"Abierto", "En proceso", "Cerrado"}
    if req_obj.estado not in estados_validos:
        return (
            jsonify(
                {
                    "error": {
                        "code": "INVALID_STATE",
                        "message": (
                            f"Estado '{req_obj.estado}' inválido. "
                            f"Debe ser uno de: {sorted(list(estados_validos))}"
                        ),
                    }
                }
            ),
            400,
        )

    tickets_file = _get_tickets_file()
    if not tickets_file.exists():
        return (
            jsonify(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Ticket {ticket_id} no encontrado",
                    }
                }
            ),
            404,
        )

    try:
        with open(tickets_file, "r", encoding="utf-8") as f:
            tickets = json.load(f)
    except Exception as e:
        return jsonify({"error": {"code": "READ_ERROR", "message": str(e)}}), 500

    target = None
    for t in tickets:
        if t.get("id") == ticket_id:
            target = t
            break

    if not target:
        return (
            jsonify(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Ticket {ticket_id} no encontrado",
                    }
                }
            ),
            404,
        )

    target["estado"] = req_obj.estado
    if req_obj.resolucion is not None:
        target["resolucion"] = req_obj.resolucion
    if "origen" not in target:
        target["origen"] = "app"

    try:
        with open(tickets_file, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error actualizando ticket {ticket_id}: {e}")
        return jsonify({"error": {"code": "WRITE_ERROR", "message": str(e)}}), 500

    # Sincronización con GitHub Issues al actualizar estado
    try:
        from services.github_service import GitHubIssueSyncService

        GitHubIssueSyncService.sync_ticket_status(
            ticket_id=ticket_id,
            nuevo_estado=req_obj.estado,
            resolucion=req_obj.resolucion,
        )
    except Exception as e_gh:
        logger.warning(
            f"Error no bloqueante al sincronizar estado de issue en GitHub: {e_gh}"
        )

    return jsonify(target), 200


@soporte_bp.route("/sistema/logs", methods=["GET"])
@require_api_key
def get_logs() -> Any:
    limit_str = request.args.get("limit", "20")
    try:
        limit = max(1, min(100, int(limit_str)))
    except (ValueError, TypeError):
        limit = 20

    base_dir = _get_base_dir()
    log_file = base_dir / "gen_log.txt"
    entries: list[dict[str, str]] = []

    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = [line.strip() for line in f if line.strip()]

            # Leer en orden cronológico inverso (más reciente primero)
            for line in reversed(lines):
                if len(entries) >= limit:
                    break
                match = re.match(
                    r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*(.*)$",
                    line,
                )
                if match:
                    ts_raw, msg = match.group(1), match.group(2)
                    try:
                        dt = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
                        ts = dt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        ts = ts_raw
                else:
                    ts = get_now_py().strftime("%d/%m/%Y %H:%M:%S")
                    msg = line

                msg_lower = msg.lower()
                if (
                    "❌" in msg
                    or "error" in msg_lower
                    or "exception" in msg_lower
                    or "fail" in msg_lower
                ):
                    nivel = "ERROR"
                elif "⚠️" in msg or "warn" in msg_lower or "advertencia" in msg_lower:
                    nivel = "WARN"
                else:
                    nivel = "INFO"

                entries.append(
                    {
                        "timestamp": ts,
                        "nivel": nivel,
                        "mensaje": msg,
                    }
                )
        except Exception as e:
            logger.warning(f"Error leyendo logs desde {log_file}: {e}")

    # Fallback estructurado si el archivo no existe o está vacío
    if not entries:
        entries = [
            {
                "timestamp": get_now_py().strftime("%d/%m/%Y %H:%M:%S"),
                "nivel": "INFO",
                "mensaje": "Servidor backend Gamma operativo en WSGI.",
            },
            {
                "timestamp": get_now_py().strftime("%d/%m/%Y %H:%M:%S"),
                "nivel": "INFO",
                "mensaje": "Mobile API Blueprint v2.0.0 activo.",
            },
        ]

    response = jsonify(entries)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200


@soporte_bp.route("/webhooks/github", methods=["POST"])
def github_webhook() -> Any:
    """Receptor público de webhooks de GitHub para sincronización reactiva."""
    from services.github_service import GitHubWebhookService

    # 1. Validación de firma HMAC si GITHUB_WEBHOOK_SECRET está configurado
    signature_header = request.headers.get("X-Hub-Signature-256")
    payload_bytes = request.get_data()

    if not GitHubWebhookService.verify_signature(payload_bytes, signature_header):
        logger.warning(
            "Intento de webhook de GitHub con firma HMAC inválida o ausente."
        )
        return (
            jsonify(
                {
                    "error": {
                        "code": "INVALID_SIGNATURE",
                        "message": (
                            "Firma HMAC de GitHub no coincide con el secret configurado."
                        ),
                    }
                }
            ),
            401,
        )

    event_type = request.headers.get("X-GitHub-Event", "")

    # 2. Manejo de Ping
    if event_type == "ping":
        logger.info("GitHub Webhook ping recibido exitosamente.")
        return (
            jsonify(
                {
                    "status": "pong",
                    "message": "GitHub Webhook listener operational",
                }
            ),
            200,
        )

    # 3. Manejo de Eventos de Issues
    if event_type == "issues":
        data = request.get_json(silent=True) or {}
        action = data.get("action", "")
        issue_data = data.get("issue", {})

        tickets_file = _get_tickets_file()
        resultado = GitHubWebhookService.process_issue_event(
            action=action,
            issue_data=issue_data,
            tickets_file_path=tickets_file,
        )

        # Notificación reactiva al Telegram del Administrador si el ticket fue procesado
        if resultado.get("status") == "processed":
            try:
                chat_id = os.getenv("CHAT_ID")
                if chat_id:
                    from flask_app import bot_instance

                    if (
                        bot_instance
                        and hasattr(bot_instance, "bot")
                        and bot_instance.bot
                    ):
                        accion_emoji = (
                            "✅" if resultado.get("nuevo_estado") == "Cerrado" else "🔄"
                        )
                        bot_instance.bot.send_message(
                            int(chat_id),
                            f"{accion_emoji} <b>Actualización de Ticket desde GitHub</b>\n\n"
                            f"🆔 <b>Ticket:</b> <code>{resultado.get('ticket_id')}</code>\n"
                            f"📌 <b>Estado:</b> {resultado.get('nuevo_estado')}\n"
                            f"🐙 <b>Issue:</b> #{resultado.get('issue_number')}\n"
                            f"⚡ <b>Acción:</b> <code>{action}</code>",
                            parse_mode="HTML",
                        )
            except Exception as e_tg:
                logger.warning(f"Error no bloqueante notificando a Telegram: {e_tg}")

        return jsonify(resultado), 200

    # 4. Cualquier otro evento no manejado se acepta sin error (para evitar retries de GitHub)
    return (
        jsonify(
            {
                "status": "ignored",
                "reason": f"Event '{event_type}' not handled",
            }
        ),
        200,
    )
