import telebot
import os
import pytz

from logger_config import setup_logger
logger = setup_logger("bot")
from dotenv import load_dotenv
from logic.logic import AgenteAutonomoHoras, AgenteAsistenciaMaterias, EstadoGestor
from logic.financiero import AgenteFinanciero
from telebot.types import BotCommand
from datetime import datetime

tz_py = pytz.timezone('America/Buenos_Aires')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

class GAMMA:
    def __init__(self):
        self.token = os.getenv('TOKEN')
        self.sheet_id = os.getenv('SPREADSHEET_ID')

        if not all([self.token, self.sheet_id]):
            raise ValueError("Faltan variables en el archivo .env (TOKEN, CHAT_ID o SPREADSHEET_ID)")

        self.bot = telebot.TeleBot(self.token, threaded=False)



        self.agente_excel = AgenteAutonomoHoras(spreadsheet_id=self.sheet_id)
        self.agente_materias = AgenteAsistenciaMaterias()
        self.agente_financiero = AgenteFinanciero(spreadsheet_id=self.sheet_id)
        
        self._registrar_manejadores()

    def _registrar_manejadores(self):
        from com.handlers.base import register_base_handlers
        from com.handlers.asistencia import register_asistencia_handlers
        from com.handlers.finanzas import register_finanzas_handlers
        from com.handlers.avisos import register_avisos_handlers
        
        register_base_handlers(self.bot, self)
        register_asistencia_handlers(self.bot, self)
        register_finanzas_handlers(self.bot, self)
        register_avisos_handlers(self.bot, self)
