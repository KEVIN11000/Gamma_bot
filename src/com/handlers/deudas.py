from __future__ import annotations

from typing import Any
from telebot import TeleBot
import shlex

from com.core.errors import safe_handler
from com.core.security import auth_required
from logger_config import setup_logger
from logic.financiero import (
    create_debt,
    get_active_debts,
    register_payment,
    execute_monthly_closing,
    simulate_project,
    approve_project,
    proyectar_cola_deudas,
    simular_impacto_abono,
    obtener_cronograma_vencimientos
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
                bot.reply_to(message, "Uso: /nueva_deuda \"Entidad\" \"Concepto\" <Monto> <Cuotas> <Primer_Venc> [Dia_Vencimiento]")
                return
            entity = parts[1]
            concept = parts[2]
            amount = int(parts[3])
            quotas = int(parts[4])
            first_due = parts[5]
            
            dia_venc = int(parts[6]) if len(parts) > 6 else 0
            
            debt_id = create_debt(entity, concept, amount, quotas, first_due, dia_vencimiento=dia_venc)
            bot.reply_to(message, f"Deuda creada con ID: `{debt_id}`", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["estrategia", "cola_deudas"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_estrategia(message):
        try:
            parts = shlex.split(message.text)
            criterio = "prioridad"
            if len(parts) > 1 and parts[1] in ["saldo", "prioridad"]:
                criterio = parts[1]
                
            res = proyectar_cola_deudas(criterio)
            margen = res["margen_ataque"]
            proy = res["proyeccion"]
            
            if not proy:
                bot.reply_to(message, "No hay deudas en la cola.")
                return
                
            response = f"🎯 *Estrategia de Pago Bola de Nieve* ({criterio})\n"
            response += f"💰 *Margen de Ataque Base:* Gs. {margen:,}\n\n".replace(",", ".")
            
            for i, p in enumerate(proy, 1):
                estado = "🔴 VENCIDA" if p["vencida"] else "🟢 Al día"
                response += (
                    f"{i}. *{p['nombre']}* (ID: `{p.get('id', 'N/A')}`)\n"
                    f"   Estado: {estado}\n"
                    f"   Pago mensual proyectado: Gs. {p['pago_mensual_proyectado']:,}\n".replace(",", ".") +
                    f"   Meses estimados: {p['meses_estimados']} (Fin: {p['fecha_fin']})\n\n"
                )
            bot.reply_to(message, response, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["foco"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_foco(message):
        try:
            res = proyectar_cola_deudas("prioridad")
            proy = res["proyeccion"]
            if not proy:
                bot.reply_to(message, "No hay deudas en foco.")
                return
            foco = proy[0]
            bot.reply_to(message, f"🎯 *Foco Actual:* {foco['nombre']} (ID: `{foco.get('id', 'N/A')}`)\nPago mensual proyectado: Gs. {foco['pago_mensual_proyectado']:,}\nMeses estimados: {foco['meses_estimados']}".replace(",", "."), parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["evaluar_abono"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_evaluar_abono(message):
        try:
            parts = shlex.split(message.text)
            if len(parts) < 3:
                bot.reply_to(message, "Uso: /evaluar_abono <Monto_Extra> <ID_Deuda>")
                return
            monto = int(parts[1])
            debt_id = parts[2]
            
            res = simular_impacto_abono(monto, debt_id)
            if "error" in res:
                bot.reply_to(message, f"Error: {res['error']}")
                return
                
            response = (
                f"📊 *Simulación de Abono Extra*\n"
                f"Monto Extra: Gs. {monto:,}\n".replace(",", ".") +
                f"Saldo Anterior: Gs. {res['saldo_anterior']:,}\n".replace(",", ".") +
                f"Saldo Nuevo: Gs. {res['saldo_nuevo']:,}\n".replace(",", ".") +
                f"Meses Ahorrados: {res['meses_ahorrados']}\n"
                f"Meses Restantes (Nueva Proyección): {res['meses_restantes']}"
            )
            bot.reply_to(message, response, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["vencimientos"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_vencimientos(message):
        try:
            res = obtener_cronograma_vencimientos()
            vencimientos = res["vencimientos"]
            if not vencimientos:
                bot.reply_to(message, "No hay vencimientos programados.")
                return
                
            response = f"📅 *Vencimientos del Mes ({res['mes_actual']})*\n\n"
            for v in vencimientos:
                response += (
                    f"Día {v['dia_vencimiento']}: *{v['nombre']}* (ID: `{v['id']}`)\n"
                    f"   Cuota: Gs. {v['cuota']:,} | Saldo: Gs. {v['saldo']:,}\n\n".replace(",", ".")
                )
            bot.reply_to(message, response, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=["deudas"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_deudas(message):
        def _safe_int(v):
            try:
                if isinstance(v, str):
                    v = v.strip()
                if not v or v == "N/A":
                    return 0
                return int(float(v))
            except Exception:
                return 0
        try:
            parts = shlex.split(message.text)
            debt_id = parts[1] if len(parts) > 1 else None
            debts = get_active_debts(debt_id)
            if not debts:
                bot.reply_to(message, "No hay deudas activas.")
                return
            response = "📋 *Deudas activas:*\n"
            for d in debts:
                nombre = d.get('Nombre', 'N/A')
                monto = d.get('Monto_Inicial', 0)
                cuota = d.get('Cuota_Referencia_Gs', 'N/A')
                saldo = d.get('Saldo_Actual', 0)
                response += (
                    f"─────────────────\n"
                    f"🆔 `{d.get('ID_Obligacion', 'N/A')}`\n"
                    f"📝 {nombre}\n"
                    f"💰 Monto: Gs. {_safe_int(monto):,}\n".replace(",", ".") +
                    f"📊 Cuota Ref: Gs. {_safe_int(cuota):,}\n".replace(",", ".") +
                    f"💳 Saldo: Gs. {_safe_int(saldo):,}\n".replace(",", ".")
                )
            bot.reply_to(message, response, parse_mode="Markdown")
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
