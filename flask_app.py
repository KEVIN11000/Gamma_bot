from flask import Flask, request
import telebot
import os
import threading  # 🚨 1. IMPORTANTE: Importamos la librería de hilos
from com.bot import GAMMA

app = Flask(__name__)
bot_instance = GAMMA()

@app.route('/' + os.environ.get('TOKEN'), methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)

    # 🚨 2. LA CLAVE: Procesamos el mensaje en un "hilo" en segundo plano.
    # Esto ejecuta bot.py sin hacer esperar a Flask.
    threading.Thread(target=bot_instance.bot.process_new_updates, args=([update],)).start()

    # 🚨 3. RESPUESTA INMEDIATA: Le cerramos la boca a Telegram en menos de 0.1 segundos.
    # Así Telegram se queda tranquilo y NO reintenta el mensaje.
    return "OK", 200

@app.route('/set_webhook')
def set_webhook():
    # Cambia 'tu_usuario' por tu nombre de usuario de PythonAnywhere
    url_app = "https://kevin11000.pythonanywhere.com"
    success = bot_instance.bot.set_webhook(url=f"{url_app}/{bot_instance.token}")
    if success:
        return "✅ Webhook configurado con éxito", 200
    return "❌ Error al configurar Webhook", 500

@app.route('/')
def home():
    return "Bot de Marcación Activo", 200