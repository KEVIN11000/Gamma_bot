import os
from flask_app import app, bot_instance

if __name__ == "__main__":
    print("======================================================")
    print("🚀 INICIANDO SERVIDOR LOCAL PARA PRUEBAS (V1.4.1)")
    print("======================================================")
    
    # Nos aseguramos de que el bot quite cualquier webhook anterior
    bot_instance.bot.remove_webhook()
    print("✅ Webhook removido. Iniciando modo Polling...")
    print("🤖 El bot ya está escuchando tus mensajes en Telegram.")
    
    # Levantamos el bot en modo polling (escucha continua)
    bot_instance.bot.infinity_polling()
