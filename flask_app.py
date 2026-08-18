from __future__ import annotations
from typing import Any
from flask import Flask, request, abort
import telebot
import os
import time
import subprocess
import hmac
import hashlib
import json
from logger_config import setup_logger
from com.bot import GAMMA
from logic.cron_jobs import resumen_semanal, notificacion_clima, rotar_logs
import config
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = setup_logger("flask")
app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=["10 per minute"])
limiter.init_app(app)
bot_instance = GAMMA()
from pathlib import Path
base_path = Path(__file__).resolve().parent

@app.route('/', methods=['POST'])
@limiter.limit("10/min")
def webhook() -> Any:
    # Verify custom header token
    token_header = request.headers.get('X-Bot-Token')
    if token_header != config.TOKEN:
        abort(401, "Invalid token")
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
            try: os.remove(deploy_file) 
            except: pass

    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)

    # Procesamiento síncrono: en el tier gratuito de PythonAnywhere (1 worker),
    # un hilo en segundo plano -> ser destruido cuando la petición HTTP finaliza.
    # El procesamiento síncrono garantiza que el mensaje se procese completamente.
    try:
        bot_instance.bot.process_new_updates([update])
    except Exception as e:
        logger.error(f"Error procesando update: {e}")

    return "OK", 200

@app.route('/set_webhook')
def set_webhook() -> Any:
    url_app = "https://kevin11000.pythonanywhere.com"
    success = bot_instance.bot.set_webhook(url=f"{url_app}/{bot_instance.token}")
    if success:
        return "✅ Webhook configurado con éxito", 200
    return "❌ Error al configurar Webhook", 500

@app.route('/')
def home() -> Any:
    return "Bot de Marcación Activo", 200

# ── Auto-deploy desde GitHub ──────────────────────────────────────────────────
@limiter.limit("10 per minute")
@app.route('/deploy', methods=['POST'])
def deploy() -> Any:
    """
    Endpoint llamado por el webhook de GitHub en cada push a Main-stable.
    Valida la firma HMAC-SHA256 con GITHUB_WEBHOOK_SECRET para seguridad.
    Tras el git pull, toca el archivo WSGI para forzar el reload de la app
    en PythonAnywhere (funciona en cuentas gratuitas sin API externa).
    """
    # Validate GitHub webhook signature if secret is set (mandatory in production)
    if config.GITHUB_WEBHOOK_SECRET:
        secret = config.GITHUB_WEBHOOK_SECRET.encode()
        signature_header = request.headers.get('X-Hub-Signature-256', '')
        body = request.get_data()
        expected = 'sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature_header):
            abort(403, "Firma inválida")
    elif config.is_production():
        abort(403, "Missing GITHUB_WEBHOOK_SECRET")
    # If no secret and not production, skip signature verification (development mode)

    # 2. Filtrar: solo actuar en push a Main-stable
    payload = request.get_json(silent=True) or {}
    ref = payload.get('ref', '')
    if ref and ref != 'refs/heads/Main-stable':
        return f"Push en '{ref}' ignorado (no es Main-stable)", 200

    # 3. Ejecutar git pull
    wsgi_path = "/var/www/kevin11000_pythonanywhere_com_wsgi.py"
    try:
        resultado = subprocess.run(
            ["git", "pull", "origin", "Main-stable"],
            cwd=base_path,
            capture_output=True,
            text=True,
            timeout=30
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
                    f"🚀 <b>¡Actualización completada!</b>\nEl autodeploy descargó la nueva versión <b>({version})</b> y el servidor se ha reiniciado.\n\nEscribe /start para ver el menú de comandos.",
                    parse_mode="HTML"
                )
                logger.info("[deploy] Mensaje enviado correctamente.")

                # Guardar el ID del mensaje para que el webhook lo borre en la próxima interacción
                deploy_data = {
                    "chat_id": chat_id,
                    "msg_id": msg.message_id,
                    "time": time.time()
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
def _validar_cron_secret() -> Any:
    """Verify the secret token for cron endpoints.
    Reads CRON_SECRET from the environment on each request, allowing
    all calls in development when the variable is unset or empty.
    """
    secret = os.getenv('CRON_SECRET')
    # If no secret is defined, allow in non‑production environments
    if not secret:
        return not config.is_production()
    token_enviado = request.headers.get('X-Cron-Secret', '') or request.args.get('secret', '')
    return token_enviado == secret


@limiter.limit("10 per minute")
@app.route('/cron/resumen-semanal', methods=['GET', 'POST'])
def cron_resumen_semanal() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get('CHAT_ID')
    spreadsheet_id = os.environ.get('SPREADSHEET_ID')
    if not chat_id or not spreadsheet_id:
        return "❌ CHAT_ID o SPREADSHEET_ID no configurados.", 500
    exito = resumen_semanal(bot_instance.bot, chat_id, spreadsheet_id)
    return ("✅ Resumen semanal enviado.", 200) if exito else ("❌ Error en resumen semanal.", 500)


@limiter.limit("10 per minute")
@app.route('/cron/clima', methods=['GET', 'POST'])
def cron_clima() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get('CHAT_ID')
    if not chat_id:
        return "❌ CHAT_ID no configurado.", 500
    exito = notificacion_clima(bot_instance.bot, chat_id)
    return ("✅ Notificación climática enviada.", 200) if exito else ("❌ Error en clima.", 500)


@limiter.limit("10 per minute")
@app.route('/cron/rotar-logs', methods=['GET', 'POST'])
def cron_rotar_logs() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    exito = rotar_logs()
    return ("✅ Logs rotados correctamente.", 200) if exito else ("❌ Error al rotar logs.", 500)


@limiter.limit("10 per minute")
@app.route('/cron/cierre-mensual', methods=['GET', 'POST'])
def cron_cierre_mensual() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get('CHAT_ID')
    if not chat_id:
        return "❌ CHAT_ID no configurado.", 500
    from logic.cron_jobs import informe_estadistico_mensual
    exito = informe_estadistico_mensual(bot_instance, chat_id)
    return ("✅ Informe estadístico ejecutado y reportes enviados.", 200) if exito else ("❌ Error en informe.", 500)


@limiter.limit("10 per minute")
@app.route('/cron/asesor-ia', methods=['GET', 'POST'])
def cron_asesor_ia() -> Any:
    if not _validar_cron_secret():
        abort(403, "Token inválido")
    chat_id = os.environ.get('CHAT_ID')
    if not chat_id:
        return "❌ CHAT_ID no configurado.", 500
    from logic.cron_jobs import alerta_asesor_financiero
    exito = alerta_asesor_financiero(bot_instance, chat_id)
    return ("✅ Insights del Asesor IA enviados.", 200) if exito else ("❌ Error en Asesor IA.", 500)

