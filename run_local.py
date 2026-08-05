import os
from flask_app import app, bot_instance

if __name__ == "__main__":
    print("======================================================")
    print("🚀 INICIANDO SERVIDOR LOCAL PARA PRUEBAS (V1.3)")
    print("======================================================")
    
    # Nos aseguramos de que el bot quite cualquier webhook anterior
    bot_instance.bot.remove_webhook()
    print("✅ Webhook removido (El bot no escuchará mensajes entrantes localmente,")
    print("   pero el endpoint del Cron Job funcionará perfectamente).")
    
    print("\n🌐 PARA PROBAR EL CRON, ABRE EN TU NAVEGADOR:")
    secret = os.environ.get('CRON_SECRET', 'PON_TU_SECRETO_AQUI')
    print(f"👉 http://127.0.0.1:5000/cron/revisar_avisos/{secret}\n")
    
    # Levantamos Flask en el puerto 5000
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
