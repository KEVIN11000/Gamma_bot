import os
from dotenv import load_dotenv

# Forzar modo desarrollo local
# logger import removed – using setup_logger below
# os.environ["MODO_DESARROLLADOR"] = "true"  # Removed forced dev mode; configure via .env or CLI

from com.bot import GAMMA

from logger_config import setup_logger
logger = setup_logger("run_local")
logger.info("Iniciando Gamma Bot en modo LOCAL (Polling)...")
logger.info("Presiona Ctrl+C para detener.")

# Eliminar Webhook activo si lo hubiera
bot_instance = GAMMA()
try:
    # Ensure any previous polling is stopped to avoid conflict
    bot_instance.bot.stop_polling()
    bot_instance.bot.remove_webhook()
    logger.info("Webhook eliminated and previous polling stopped, initiating new polling...")
    bot_instance.bot.polling(none_stop=True)
except Exception as e:
    logger.error(f"Error en polling: {e}")
