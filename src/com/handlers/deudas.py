from __future__ import annotations

from typing import Any
from telebot import TeleBot
import shlex

from src.com.core.errors import safe_handler
from src.com.core.security import auth_required
from src.logger_config import setup_logger
from src.logic.financiero import (
    create_debt,
    get_active_debts,
    register_payment,
    execute_monthly_closing,
    simulate_project,
    approve_project
)

logger = setup_logger("deudas_handler")

def register_deudas_handlers(bot: TeleBot, gamma_app: Any) -> Any:
    
    @bot.message_handler(commands=["nueva_deuda"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda(message):
        try:
            parts = shlex.split(message.text)
            if len(parts) < 6:
                bot.reply_to(message, "Uso: /nueva_deuda \"Entidad\" \"Concepto\" <Monto> <Cuotas> <Primer_Venc>")
                return
            entity = parts[1]
            concept = parts[2]
            amount = int(parts[3])
            quotas = int(parts[4])
            first_due = parts[5]
            
            debt_id = create_debt(entity, concept, amount, quotas, first_due)
            bot.reply_to(message, f"Deuda creada con ID: {debt_id}")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["deudas"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_deudas(message):
        try:
            parts = shlex.split(message.text)
            debt_id = parts[1] if len(parts) > 1 else None
            debts = get_active_debts(debt_id)
            if not debts:
                bot.reply_to(message, "No hay deudas activas.")
                return
            response = "Deudas activas:\n"
            for d in debts:
                response += f"- ID: {d.get('id_deuda')} | Entidad: {d.get('entidad')} | Monto: {d.get('monto_total')}\n"
            bot.reply_to(message, response)
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["abonar"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_abonar(message):
        try:
            parts = shlex.split(message.text)
            if len(parts) < 4:
                bot.reply_to(message, "Uso: /abonar <ID_Deuda> <Monto> <Fecha>")
                return
            debt_id = parts[1]
            amount = int(parts[2])
            date = parts[3]
            
            register_payment(debt_id, amount, date)
            bot.reply_to(message, f"Abono registrado para la deuda {debt_id}")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")
            
    @bot.message_handler(commands=["cierre_mensual"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_cierre_mensual(message):
        try:
            parts = shlex.split(message.text)
            if len(parts) < 3:
                bot.reply_to(message, "Uso: /cierre_mensual <Mes> <Año>")
                return
            month = int(parts[1])
            year = int(parts[2])
            
            drive_id = execute_monthly_closing(month, year)
            bot.reply_to(message, f"Cierre mensual ejecutado. Backup ID: {drive_id}")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["simular"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_simular(message):
        try:
            parts = shlex.split(message.text)
            if len(parts) < 3:
                bot.reply_to(message, "Uso: /simular <Monto_Proyecto> <Meses> [Concepto]")
                return
            monto = int(parts[1])
            meses = int(parts[2])
            concept = " ".join(parts[3:]) if len(parts) > 3 else "N/A"
            
            # Estado de carga inmediato
            msg_carga = bot.reply_to(message, "⏳ *Consultando presupuesto y calculando viabilidad...*", parse_mode="Markdown")
            
            # Procesamiento (llamadas a la API de Sheets)
            response_text = simulate_project(monto, meses, concept)
            
            # Reemplazamos el mensaje de carga con el resultado final
            bot.edit_message_text(
                chat_id=message.chat.id, 
                message_id=msg_carga.message_id, 
                text=response_text, 
                parse_mode="Markdown"
            )
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["aprobar_proyecto"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_aprobar_proyecto(message):
        try:
            parts = shlex.split(message.text)
            if len(parts) < 2:
                bot.reply_to(message, "Uso: /aprobar_proyecto <ID_Proyecto>")
                return
            project_id = parts[1]
            approve_project(project_id)
            bot.reply_to(message, f"Proyecto {project_id} aprobado.")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")
