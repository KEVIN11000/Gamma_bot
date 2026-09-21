from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from telebot import TeleBot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

from com.core.errors import safe_handler
from com.core.security import auth_required
from logger_config import setup_logger

logger = setup_logger("base_handler")


def _registrar_comandos_menu(bot: TeleBot) -> Any:
    comandos = [
        BotCommand("start", "Mostrar menú principal"),
        BotCommand("comandos", "Ver lista de todos los comandos disponibles."),
        BotCommand("gasto", "Registrar un nuevo gasto (ej. '/gasto 15000 taxi')."),
        BotCommand("ingreso", "Registrar un nuevo ingreso."),
        BotCommand("balance", "Ver el balance financiero mensual."),
        BotCommand("nueva_deuda", "Registrar un nuevo compromiso financiero."),
        BotCommand("deudas", "Ver estado de cuentas activas y barra de progreso."),
        BotCommand("abonar", "Registrar un pago parcial o total a una deuda."),
        BotCommand("cierre_mensual", "Ejecutar el cierre financiero mensual."),
        BotCommand("simular", "Simular el impacto financiero de un proyecto."),
        BotCommand("marcar", "Registrar entrada/salida general."),
        BotCommand("marcar_materia", "Registrar asistencia a materias."),
        BotCommand("reporte", "Generar reporte PDF de un período anterior."),
        BotCommand("aviso", "Agendar un hito o recordatorio con IA."),
        BotCommand("avisos", "Ver lista de avisos activos."),
        BotCommand("cierre", "Ejecutar cierre de período de marcaciones."),
        BotCommand("soporte", "Reportar un bug, error o sugerencia."),
    ]

    if os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true":
        comandos.append(BotCommand("debug", "Ver logs recientes del sistema."))

    bot.set_my_commands(comandos)


logger.info("✅ Menú de comandos actualizado.")


def register_base_handlers(bot: TeleBot, gamma_app: Any) -> Any:
    @bot.message_handler(commands=["cancelar"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_cancelar(message):
        from com.core.states import clear_state, has_state
        from logic.logic import EstadoGestor

        user_id = message.from_user.id if message.from_user else message.chat.id
        chat_id = message.chat.id
        tenia_estado = has_state(user_id) or has_state(chat_id)
        clear_state(user_id)
        if chat_id != user_id:
            clear_state(chat_id)
        EstadoGestor.pop(chat_id)
        EstadoGestor.pop(f"iva_{chat_id}")
        EstadoGestor.pop(f"reporte_{chat_id}")
        if tenia_estado:
            bot.reply_to(message, "✅ Operación cancelada. El estado ha sido limpiado.")
        else:
            bot.reply_to(message, "❌ Operación cancelada.")

    @bot.message_handler(commands=["debug"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_debug(message):
        modo_dev = os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true"
        if not modo_dev:
            bot.reply_to(
                message,
                "🔒 El comando de depuración está desactivado en este entorno de producción.",
            )
            return

        partes = message.text.split(" ", 1)
        tipo_log = partes[1].strip().lower() if len(partes) > 1 else "app"

        archivos = {
            "app": "gen_log.txt",
            "error": "/var/log/kevin11000.pythonanywhere.com.error.log",
            "server": "/var/log/kevin11000.pythonanywhere.com.server.log",
            "access": "/var/log/kevin11000.pythonanywhere.com.access.log",
        }

        if tipo_log not in archivos:
            msg = (
                "⚠️ *Comando incorrecto.*\nUsa:\n"
                "`/debug app` (logs internos)\n"
                "`/debug error` (logs de PA)\n"
                "`/debug server` (logs server)\n"
                "`/debug access` (logs web)"
            )
            bot.reply_to(message, msg, parse_mode="Markdown")
            return

        ruta_archivo = archivos[tipo_log]

        if Path(ruta_archivo).exists():
            with open(ruta_archivo, "r", encoding="utf-8", errors="replace") as f:
                lineas = f.readlines()
                ultimas = "".join(lineas[-20:])
            if not ultimas.strip():
                ultimas = "[El archivo existe pero está vacío]"
            bot.reply_to(
                message,
                f"🛠️ *ÚLTIMOS LOGS ({tipo_log.upper()}):*\n```text\n{ultimas[-3000:]}\n```",
                parse_mode="Markdown",
            )
        else:
            bot.reply_to(
                message,
                f"📭 El archivo `{ruta_archivo}` no existe.\n_(Normal si estás corriendo el bot en Windows localmente)_",
                parse_mode="Markdown",
            )

    def get_menu_raiz():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("💰 Finanzas", callback_data="menu:finanzas"),
            InlineKeyboardButton("🕐 Asistencia", callback_data="menu:asistencia"),
            InlineKeyboardButton("⚙️ Administración", callback_data="menu:admin"),
        )
        return kb

    def get_menu_finanzas():
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("Ver Balance", callback_data="accion:balance"))
        kb.row(
            InlineKeyboardButton("Registrar Movimiento", callback_data="menu:reg_mov")
        )
        kb.row(InlineKeyboardButton("Cola de Deudas", callback_data="menu:cola_deudas"))
        kb.row(InlineKeyboardButton("Simular Proyecto", callback_data="accion:simular"))
        kb.row(InlineKeyboardButton("⬅ Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_asistencia():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("Marcar Entrada/Salida", callback_data="accion:marcar")
        )
        kb.row(
            InlineKeyboardButton("Generar Reporte PDF", callback_data="accion:reporte")
        )
        kb.row(InlineKeyboardButton("Avisos", callback_data="accion:avisos"))
        kb.row(InlineKeyboardButton("⬅ Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_admin():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton(
                "Ejecutar Cierre Mensual", callback_data="accion:cierre_mensual"
            )
        )
        kb.row(InlineKeyboardButton("Ver Logs", callback_data="accion:debug"))
        kb.row(InlineKeyboardButton("⬅ Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_reg_mov():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("💸 Gasto", callback_data="accion:gasto"),
            InlineKeyboardButton("💰 Ingreso", callback_data="accion:ingreso"),
        )
        kb.row(InlineKeyboardButton("⬅ Volver", callback_data="menu:finanzas"))
        return kb

    def get_menu_cola_deudas():
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("Ver Deudas", callback_data="accion:deudas"))
        kb.row(InlineKeyboardButton("Nueva Deuda", callback_data="accion:nueva_deuda"))
        kb.row(InlineKeyboardButton("Abonar", callback_data="accion:abonar"))
        kb.row(InlineKeyboardButton("⬅ Volver", callback_data="menu:finanzas"))
        return kb

    @bot.message_handler(commands=["start"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_start(message):
        _registrar_comandos_menu(bot)

        texto = "🤖 *Menú Principal GAMMA*\nSelecciona una opción:"
        bot.reply_to(
            message, texto, parse_mode="Markdown", reply_markup=get_menu_raiz()
        )

    @bot.message_handler(commands=["comandos"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_comandos(message):
        modo_dev = os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true"
        texto_debug = "🛠️ /debug   — Ver logs de errores internos\n" if modo_dev else ""

        # Leer archivo VERSION
        version = "1.x"
        base_path = Path(__file__).resolve().parents[3]
        version_path = base_path / "VERSION"
        if version_path.exists():
            with open(version_path, "r") as f:
                version = f.read().strip()

        texto = (
            f"🤖 *Bot de Gestión Avanzada (GAMMA)* `{version}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Menú de comandos sincronizado ✅\n\n"
            "*Finanzas & Deudas:*\n"
            "💸 /gasto — Registrar gasto por texto\n"
            "💰 /ingreso — Registrar ingreso\n"
            "📊 /balance — Ver tu balance\n"
            "📝 /nueva\\_deuda — Alta de deudas o cuentas\n"
            "💳 /deudas — Ver estado de cuentas activas\n"
            "💵 /abonar — Registrar un pago\n"
            "🔮 /simular — Proyectar impacto de gastos\n"
            "📦 /cierre\\_mensual — Ejecutar cierre del mes\n"
            "📷 Envia una foto de factura para leerla (OCR)\n\n"
            "*Asistencia:*\n"
            "▶️ /marcar  — Registrar entrada o salida\n"
            "📚 /marcar\\_materia — Asistencia a materias\n"
            "📄 /reporte — Generar PDF\n\n"
            "*Avisos:*\n"
            "✍️ /aviso   — Agendar recordatorios\n"
            "📋 /avisos  — Gestionar recordatorios\n"
            f"{texto_debug}"
        )
        bot.reply_to(message, texto, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("menu:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_menu(call):
        bot.answer_callback_query(call.id)
        menu_type = call.data.split(":")[1]

        menus = {
            "raiz": get_menu_raiz(),
            "finanzas": get_menu_finanzas(),
            "asistencia": get_menu_asistencia(),
            "admin": get_menu_admin(),
            "reg_mov": get_menu_reg_mov(),
            "cola_deudas": get_menu_cola_deudas(),
        }

        if menu_type in menus:
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=menus[menu_type],
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("accion:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_accion(call):
        bot.answer_callback_query(call.id)
        accion = call.data.split(":")[1]

        fake_msg = call.message
        fake_msg.text = f"/{accion}"
        fake_msg.from_user = call.from_user

        bot.process_new_messages([fake_msg])
