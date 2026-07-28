from flask import Flask, request, abort
import telebot
import os
import threading
import subprocess
import hmac
import hashlib
from com.bot import GAMMA

app = Flask(__name__)
bot_instance = GAMMA()

@app.route('/' + os.environ.get('TOKEN'), methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)

    # Procesamos el mensaje en un hilo en segundo plano para no bloquear Flask
    threading.Thread(target=bot_instance.bot.process_new_updates, args=([update],)).start()

    # Respuesta inmediata para que Telegram no reintente
    return "OK", 200

@app.route('/set_webhook')
def set_webhook():
    url_app = "https://kevin11000.pythonanywhere.com"
    success = bot_instance.bot.set_webhook(url=f"{url_app}/{bot_instance.token}")
    if success:
        return "✅ Webhook configurado con éxito", 200
    return "❌ Error al configurar Webhook", 500

@app.route('/')
def home():
    return "Bot de Marcación Activo", 200

# ── Auto-deploy desde GitHub ──────────────────────────────────────────────────
@app.route('/deploy', methods=['POST'])
def deploy():
    """
    Endpoint llamado por el webhook de GitHub en cada push a Main-stable.
    Valida la firma HMAC-SHA256 con GITHUB_WEBHOOK_SECRET para seguridad.
    Tras el git pull, toca el archivo WSGI para forzar el reload de la app
    en PythonAnywhere (funciona en cuentas gratuitas sin API externa).
    """
    secret = os.environ.get('GITHUB_WEBHOOK_SECRET', '').encode()

    # 1. Verificar firma de GitHub
    if secret:
        signature_header = request.headers.get('X-Hub-Signature-256', '')
        body = request.get_data()
        expected = 'sha256=' + hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature_header):
            abort(403, "Firma inválida")

    # 2. Filtrar: solo actuar en push a Main-stable
    payload = request.get_json(silent=True) or {}
    ref = payload.get('ref', '')
    if ref and ref != 'refs/heads/Main-stable':
        return f"Push en '{ref}' ignorado (no es Main-stable)", 200

    # 3. Ejecutar git pull
    base_path = "/home/kevin11000/mysite"
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
        print(f"[deploy] git pull: {salida}", flush=True)

        if resultado.returncode != 0:
            return f"❌ git pull falló:\n{salida}", 500

        # 4. Tocar el WSGI para que PythonAnywhere recargue la app
        # (equivalente a hacer click en "Reload" en el panel web)
        if os.path.exists(wsgi_path):
            os.utime(wsgi_path, None)
            print("[deploy] WSGI tocado — app recargando...", flush=True)

        return f"✅ Deploy exitoso y app recargada:\n{salida}", 200

    except subprocess.TimeoutExpired:
        return "❌ Timeout en git pull", 500
    except Exception as e:
        return f"❌ Error en deploy: {e}", 500