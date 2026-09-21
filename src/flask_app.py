from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import time
import traceback
from pathlib import Path
from typing import Any

import telebot
from flask import Flask, abort, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import sys

sys.path.insert(0, os.path.dirname(__file__))

import config

config.validate_production_config()
from com.bot import GAMMA
from logger_config import setup_logger
from logic.cron_jobs import notificacion_clima, resumen_semanal, rotar_logs
from com.core.utils import limpiar_menus_expirados

logger = setup_logger("flask")
app = Flask(__name__)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10 per minute"],
    storage_uri="memory://",
)
limiter.init_app(app)
bot_instance = GAMMA()
base_path = Path(__file__).resolve().parent.parent


@app.route(f"/{config.TOKEN}", methods=["POST"])
@limiter.limit("10 per minute")
def webhook() -> Any:
    try:
        limpiar_menus_expirados(bot_instance.bot)
    except Exception:
        pass
    # Piggyback: Borrar mensaje de deploy si existe
    deploy_file = base_path / "deploy_msg.json"
    if deploy_file.exists():
        try:
            with open(deploy_file, "r") as f:
                data = json.load(f)
            # Borrar si pasaron más de 10 segundos
            if time.time() - data.get("time", 0) > 10:
                bot_instance.bot.delete_message(data["chat_id"], data["msg_id"])
                os.remove(deploy_file)
        except Exception as e:
            logger.error(f"Error borrando mensaje de deploy atrasado: {e}")
            try:
                os.remove(deploy_file)
            except Exception as e:
                logger.error(f"Error removing deploy file: {e}")
                pass

    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)

    # Procesamiento síncrono: en el tier gratuito de PythonAnywhere (1 worker),
    # un hilo en segundo plano -> ser destruido cuando la petición HTTP finaliza.
    # El procesamiento síncrono garantiza que el mensaje se procese completamente.
    try:
        bot_instance.bot.process_new_updates([update])
    except Exception as e:
        logger.error(f"Error procesando update: {e}")

    return "OK", 200


@app.route("/set_webhook")
def set_webhook() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    url_app = "https://kevin11000.pythonanywhere.com"
    success = bot_instance.bot.set_webhook(url=f"{url_app}/{bot_instance.token}")
    if success:
        return "✅ Webhook configurado con éxito", 200
    return "❌ Error al configurar Webhook", 500


@app.route("/")
def home() -> Any:
    return "Bot de Marcación Activo", 200


# ── Auto-deploy desde GitHub ──────────────────────────────────────────────────
@app.route("/deploy", methods=["POST"])
@limiter.limit("10 per minute")
def deploy() -> Any:
    """
    Endpoint llamado por el webhook de GitHub en cada push a Main-stable.
    Valida la firma HMAC-SHA256 con GITHUB_WEBHOOK_SECRET para seguridad.
    Tras el git pull, toca el archivo WSGI para forzar el reload de la app
    en PythonAnywhere (funciona en cuentas gratuitas sin API externa).
    """
    # Always require webhook secret
    if not config.GITHUB_WEBHOOK_SECRET:
        abort(403, "GITHUB_WEBHOOK_SECRET no configurado")
    secret = config.GITHUB_WEBHOOK_SECRET.encode()
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    body = request.get_data()
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        abort(403, "Firma inválida")

    # 2. Filtrar: solo actuar en push a Main-stable
    payload = request.get_json(silent=True) or {}
    ref = payload.get("ref", "")
    if ref and ref != "refs/heads/Main-stable":
        return f"Push en '{ref}' ignorado (no es Main-stable)", 200

    # 3. Ejecutar git pull
    wsgi_path = "/var/www/kevin11000_pythonanywhere_com_wsgi.py"
    try:
        resultado = subprocess.run(
            ["git", "pull", "origin", "Main-stable"],
            cwd=base_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        salida = resultado.stdout.strip() or resultado.stderr.strip()
        logger.info(f"[deploy] git pull: {salida}")

        if resultado.returncode != 0:
            return f"❌ git pull falló:\n{salida}", 500

        # 4. Enviar notificación al chat primero, ANTES de recargar
        chat_id = os.getenv("CHAT_ID")
        masked_id = "None"
        if chat_id:
            try:
                cid = int(chat_id)
                masked_id = config.mask_chat_id(cid)
            except ValueError:
                masked_id = "Invalid"
        logger.info(f"[deploy] CHAT_ID leído: {masked_id}")
        if chat_id:
            try:
                # Leer versión desde archivo VERSION (ya actualizado por git pull)
                version_path = base_path / "VERSION"
                if version_path.exists():
                    with open(version_path, "r") as f:
                        version = f.read().strip()
                else:
                    version = "desconocida"
                # Sanitizar para evitar markup en Telegram
                import html

                version = html.escape(version)

                msg = bot_instance.bot.send_message(
                    chat_id,
                    f"🚀 <b>¡Actualización completada!</b>\n"
                    f"El autodeploy descargó la nueva versión "
                    f"<b>({version})</b> y el servidor se ha "
                    f"reiniciado.\n\n"
                    f"Escribe /start para ver el menú de comandos.",
                    parse_mode="HTML",
                )
                logger.info("[deploy] Mensaje enviado correctamente.")

                # Guardar el ID del mensaje para que el webhook lo borre en la próxima interacción
                deploy_data = {
                    "chat_id": chat_id,
                    "msg_id": msg.message_id,
                    "time": time.time(),
                }
                with open(base_path / "deploy_msg.json", "w") as f:
                    json.dump(deploy_data, f)

                # También intentamos borrar cualquier mensaje de deploy anterior huérfano
                old_deploy_file = base_path / "last_deploy_msg.txt"
                if old_deploy_file.exists():
                    try:
                        with open(old_deploy_file, "r") as f:
                            old_id = f.read().strip()
                        bot_instance.bot.delete_message(chat_id, int(old_id))
                        os.remove(old_deploy_file)
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"[deploy] Error enviando aviso de deploy: {e}")

        # 5. Tocar el WSGI para que PythonAnywhere recargue la app
        # (Se hace al final para no matar el worker antes de enviar el mensaje)
        if Path(wsgi_path).exists():
            os.utime(wsgi_path, None)
            logger.info("[deploy] WSGI tocado - app recargando...")

        return f"✅ Deploy exitoso y app recargada:\n{salida}", 200

    except subprocess.TimeoutExpired:
        return "❌ Timeout en git pull", 500
    except Exception as e:
        return f"❌ Error en deploy: {e}", 500


# ── Cron Jobs (llamados por cron-job.org) ────────────────────────────────────
def _validar_cron_secret() -> bool:
    """Verify the secret token for cron endpoints.
    Returns True if valid, False otherwise.
    Always requires CRON_SECRET — no bypass for any environment.
    """
    secret = os.getenv("CRON_SECRET")
    if not secret:
        return False
    token_enviado = request.headers.get("X-Cron-Secret", "")
    return hmac.compare_digest(token_enviado, secret)


@app.route("/cron/resumen-semanal", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def cron_resumen_semanal() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get("CHAT_ID")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not chat_id or not spreadsheet_id:
        return "❌ CHAT_ID o SPREADSHEET_ID no configurados.", 500
    exito = resumen_semanal(bot_instance.bot, chat_id, spreadsheet_id)
    return (
        ("✅ Resumen semanal enviado.", 200)
        if exito
        else ("❌ Error en resumen semanal.", 500)
    )


@app.route("/cron/clima", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def cron_clima() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get("CHAT_ID")
    if not chat_id:
        return "❌ CHAT_ID no configurado.", 500
    exito = notificacion_clima(bot_instance.bot, chat_id)
    return (
        ("✅ Notificación climática enviada.", 200)
        if exito
        else ("❌ Error en clima.", 500)
    )


@app.route("/cron/rotar-logs", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def cron_rotar_logs() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    exito = rotar_logs()
    return (
        ("✅ Logs rotados correctamente.", 200)
        if exito
        else ("❌ Error al rotar logs.", 500)
    )


@app.route("/cron/cierre-mensual", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def cron_cierre_mensual() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get("CHAT_ID")
    if not chat_id:
        return "❌ CHAT_ID no configurado.", 500
    from logic.cron_jobs import informe_estadistico_mensual

    exito = informe_estadistico_mensual(bot_instance, chat_id)
    return (
        ("✅ Informe estadístico ejecutado y reportes enviados.", 200)
        if exito
        else ("❌ Error en informe.", 500)
    )


@app.route("/cron/asesor-ia", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def cron_asesor_ia() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get("CHAT_ID")
    if not chat_id:
        return "❌ CHAT_ID no configurado.", 500
    from logic.cron_jobs import alerta_asesor_financiero

    exito = alerta_asesor_financiero(bot_instance, chat_id)
    return (
        ("✅ Insights del Asesor IA enviados.", 200)
        if exito
        else ("❌ Error en Asesor IA.", 500)
    )


@app.route("/cron/procesar-cola", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def cron_procesar_cola() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    from app_queue.worker import procesar_trabajos_pendientes

    procesados = procesar_trabajos_pendientes(bot_instance.bot)
    return f"✅ {procesados} trabajos procesados.", 200


@app.route("/admin/logs", methods=["GET"])
@limiter.limit("20 per minute")
def admin_logs() -> Any:
    """Devuelve las últimas líneas de gen_log.txt e incidentes registrados.
    Protegido con el header X-Cron-Secret.
    """
    if not _validar_cron_secret():
        abort(403, "Token inválido")

    try:
        lines_count = int(request.args.get("lines", 100))
    except ValueError:
        lines_count = 100

    src_dir = Path(__file__).resolve().parent
    log_candidates = [src_dir / "gen_log.txt", base_path / "gen_log.txt"]
    log_path = next((p for p in log_candidates if p.exists()), src_dir / "gen_log.txt")

    lines = []
    total = 0
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                total = len(all_lines)
                lines = [line.rstrip("\r\n") for line in all_lines[-lines_count:]]
        except Exception as e:
            logger.error(f"Error leyendo gen_log.txt: {e}")

    fallback_candidates = [
        src_dir / "incidentes_telegram.json",
        base_path / "incidentes_telegram.json",
    ]
    fallback_path = next(
        (p for p in fallback_candidates if p.exists()),
        src_dir / "incidentes_telegram.json",
    )
    fallback_tickets = []
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                fallback_tickets = json.load(f)
        except Exception:
            pass

    from datetime import datetime, timezone

    return {
        "status": "ok",
        "server_time": datetime.now(timezone.utc).isoformat(),
        "total_lines": total,
        "returned_lines": len(lines),
        "lines": lines,
        "fallback_tickets": fallback_tickets,
    }, 200


@app.errorhandler(Exception)
def handle_unexpected_error(e: Any) -> Any:
    """Manejador global de excepciones para registrar y reportar fallos a Vigía."""
    from werkzeug.exceptions import HTTPException

    if isinstance(e, HTTPException):
        return e

    logger.error(f"Error no capturado en servidor: {e}\n{traceback.format_exc()}")
    try:
        from com.core.telemetry import reportar_incidente_vigia

        tb = traceback.format_exc()
        endpoint = request.path if request else "desconocido"
        reportar_incidente_vigia(
            titulo=f"Error {type(e).__name__} en {endpoint}",
            detalle=f"Excepción no capturada en {endpoint}: {e}",
            origen="servidor",
            traceback_str=tb,
        )
    except Exception as tel_err:
        logger.error(f"Error al emitir telemetría Vigía: {tel_err}")

    return "❌ Error interno del servidor.", 500
