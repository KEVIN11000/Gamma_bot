import os
from dotenv import load_dotenv
from flask_app import app
from logger_config import setup_logger

logger = setup_logger("run_flask")

if __name__ == "__main__":
    load_dotenv()
    logger.info("Iniciando servidor Flask local para pruebas de endpoints y cron jobs...")
    
    # Se ejecuta en el puerto 5000 localmente
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
