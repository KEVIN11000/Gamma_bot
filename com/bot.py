from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import pytz
import telebot

from logger_config import setup_logger
from logic.financiero import AgenteFinanciero
from logic.logic import AgenteAsistenciaMaterias, AgenteAutonomoHoras

logger = setup_logger("bot")

tz_py = pytz.timezone("America/Buenos_Aires")
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=BASE_DIR / ".env")


class GAMMA:
    def __init__(self):
        self.token = os.getenv("TOKEN") or "dummy_token"
        self.sheet_id = os.getenv("SPREADSHEET_ID") or "dummy_sheet_id"

        if not all([self.token, self.sheet_id]):
            raise ValueError(
                "Faltan variables en el archivo .env (TOKEN, CHAT_ID o SPREADSHEET_ID)"
            )

        self.bot = telebot.TeleBot(self.token, threaded=False)

        self.agente_excel = AgenteAutonomoHoras(spreadsheet_id=self.sheet_id)
        self.agente_materias = AgenteAsistenciaMaterias()
        self.agente_financiero = AgenteFinanciero(spreadsheet_id=self.sheet_id)

        self._registrar_manejadores()

    def _registrar_manejadores(self):
        from repositories.sheets_repository import SheetsRepository
        from services.telegram_service import TelegramService

        repo = SheetsRepository()
        service = TelegramService(repo)
        service.register_handlers(self.bot, self)
