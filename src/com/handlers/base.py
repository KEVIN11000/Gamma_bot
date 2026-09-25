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
                "🚫 El comando de depuración está desactivado en este entorno de producción.",
            )
            return

        partes = message.text.split(" ", 1)

        if len(partes) == 1:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("App (gen_log)", callback_data="debug_log:app"),
                InlineKeyboardButton("Error (PA)", callback_data="debug_log:error"),
            )
            markup.row(
                InlineKeyboardButton("Server (PA)", callback_data="debug_log:server"),
                InlineKeyboardButton("Access (PA)", callback_data="debug_log:access"),
            )
            bot.reply_to(
                message,
                "🛠️ Selecciona el archivo de log a inspeccionar:",
                reply_markup=markup,
            )
            return

        tipo_log = partes[1].strip().lower()

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
                f"🔎 *ÚLTIMOS LOGS ({tipo_log.upper()}):*\n```text\n{ultimas[-3000:]}\n```",
                parse_mode="Markdown",
            )
        else:
            bot.reply_to(
                message,
                f"❌ El archivo `{ruta_archivo}` no existe.\n_(Normal si estás corriendo el bot en Windows localmente)_",
                parse_mode="Markdown",
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("debug_log:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_debug_log(call):
        tipo_log = call.data.split(":")[1]

        # Simulamos que el usuario mandó el comando directo para reusar lógica
        fake_msg = call.message
        fake_msg.text = f"/debug {tipo_log}"
        fake_msg.from_user = call.from_user

        bot.answer_callback_query(call.id)
        # Editamos el mensaje actual para quitar los botones
        bot.edit_message_text(
            f"Solicitando logs de: {tipo_log}...",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
        )

        # Procesar comando
        bot.process_new_messages([fake_msg])

    def get_menu_raiz():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton(
                "💰 Finanzas & Presup.", callback_data="menu:finanzas"
            ),
            InlineKeyboardButton("💳 Deudas & Proyecc.", callback_data="menu:deudas"),
        )
        kb.row(
            InlineKeyboardButton(
                "🕐 Asistencia & RRHH", callback_data="menu:asistencia"
            ),
            InlineKeyboardButton("📅 Avisos & Agenda", callback_data="menu:avisos"),
        )
        kb.row(
            InlineKeyboardButton("⚙️ Sistema & Soporte", callback_data="menu:sistema")
        )
        return kb

    def get_menu_finanzas():
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("Ver Balance", callback_data="accion:balance"))
        kb.row(
            InlineKeyboardButton("Registrar Gasto", callback_data="accion:gasto"),
            InlineKeyboardButton("Registrar Ingreso", callback_data="accion:ingreso"),
        )
        kb.row(InlineKeyboardButton("Presupuesto Fijo", callback_data="accion:fijos"))
        kb.row(InlineKeyboardButton("🔙 Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_deudas():
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("Ver Deudas", callback_data="accion:deudas"))
        kb.row(
            InlineKeyboardButton("Nueva Deuda", callback_data="accion:nueva_deuda"),
            InlineKeyboardButton("Abonar", callback_data="accion:abonar"),
        )
        kb.row(
            InlineKeyboardButton("Estrategia", callback_data="accion:estrategia"),
            InlineKeyboardButton("Simular Abono", callback_data="accion:evaluar_abono"),
        )
        kb.row(
            InlineKeyboardButton("Próximo Foco", callback_data="accion:foco"),
            InlineKeyboardButton("Vencimientos", callback_data="accion:vencimientos"),
        )
        kb.row(InlineKeyboardButton("🔙 Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_asistencia():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("Marcar Trabajo", callback_data="accion:marcar"),
            InlineKeyboardButton(
                "Marcar Materia", callback_data="accion:marcar_materia"
            ),
        )
        kb.row(InlineKeyboardButton("Cierre Periodo", callback_data="accion:cierre"))
        kb.row(
            InlineKeyboardButton("Generar Reporte PDF", callback_data="accion:reporte")
        )
        kb.row(InlineKeyboardButton("🔙 Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_avisos():
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("Nuevo Aviso", callback_data="accion:aviso"))
        kb.row(InlineKeyboardButton("Gestionar Avisos", callback_data="accion:avisos"))
        kb.row(InlineKeyboardButton("🔙 Volver", callback_data="menu:raiz"))
        return kb

    def get_menu_sistema():
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton(
                "Cierre Mensual Estadístico", callback_data="accion:cierre_mensual"
            )
        )
        kb.row(InlineKeyboardButton("Simular Proyecto", callback_data="accion:simular"))
        kb.row(InlineKeyboardButton("Ver Logs Internos", callback_data="accion:debug"))
        kb.row(
            InlineKeyboardButton(
                "Abrir Ticket de Soporte", callback_data="accion:soporte"
            )
        )
        kb.row(InlineKeyboardButton("🔙 Volver", callback_data="menu:raiz"))
        return kb

    @bot.message_handler(commands=["start"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_start(message):
        _registrar_comandos_menu(bot)

        version = "1.x"
        base_path = Path(__file__).resolve().parents[3]
        version_path = base_path / "VERSION"
        if version_path.exists():
            with open(version_path, "r") as f:
                version = f.read().strip()

        texto = f"?? *Men? Principal GAMMA* {version}
Selecciona una opci?n:"
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
            "deudas": get_menu_deudas(),
            "asistencia": get_menu_asistencia(),
            "avisos": get_menu_avisos(),
            "sistema": get_menu_sistema(),
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
