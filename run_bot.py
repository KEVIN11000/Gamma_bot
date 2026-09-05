import os
from dotenv import load_dotenv
from com.bot import GAMMA
from logger_config import setup_logger

logger = setup_logger("run_bot")

def main():
    # Cargar variables del .env de pruebas
    load_dotenv()
    
    logger.info("Iniciando Gamma Bot en modo Polling Local (Pruebas)...")
    
    try:
        # Instanciar el bot
        gamma = GAMMA()
        
        # Es crucial eliminar el webhook para que Telegram permita el polling local
        logger.info("Limpiando webhooks activos...")
        gamma.bot.remove_webhook()
        
        logger.info("✅ Bot listo y escuchando comandos. Presiona Ctrl+C para detener.")
        # none_stop=True asegura que el bot no se detenga por errores de red
        gamma.bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
    except KeyboardInterrupt:
        logger.info("Apagando el bot de pruebas...")
    except Exception as e:
        logger.error(f"Error fatal en el polling: {e}")

if __name__ == "__main__":
    main()
