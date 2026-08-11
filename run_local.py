import os
from dotenv import load_dotenv

# Forzar modo desarrollo local
os.environ["MODO_DESARROLLADOR"] = "true"

from com.bot import GAMMA

print("Iniciando Gamma Bot en modo LOCAL (Polling)...")
print("Presiona Ctrl+C para detener.")

# Eliminar Webhook activo si lo hubiera
bot_instance = GAMMA()
try:
    bot_instance.bot.remove_webhook()
    print("Webhook eliminado, iniciando polling...")
    bot_instance.bot.polling(none_stop=True)
except Exception as e:
    print(f"Error en polling: {e}")
