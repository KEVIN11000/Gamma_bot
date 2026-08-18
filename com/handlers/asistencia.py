from __future__ import annotations

from pathlib import Path

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from com.core.utils import reply_with_expiration

from com.core.errors import safe_handler
from com.core.security import auth_required, verificar_usuario_manual
from logger_config import setup_logger
from logic.logic import EstadoGestor
from services.asistencia_service import (
    iniciar_flujo_reporte_horas,
    generar_y_enviar_reporte_financiero,
    capturar_monto_descuento,
    generar_y_enviar_reporte,
    capturar_descuento_reporte,
    generar_y_enviar_reporte_por_hoja,
)
from com.core.utils import reply_with_expiration

logger = setup_logger("asistencia_handler")


def register_asistencia_handlers(bot: TeleBot, gamma_app: "GammaApp") -> None:

    @bot.message_handler(commands=["marcar"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_marcar(message):
        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("▶️ Marcar", callback_data="marcar_normal"),
            InlineKeyboardButton("🚪 Salida directa", callback_data="marcar_directo"),
        )
        reply_with_expiration(
            bot,
            message.chat.id,
            "¿Qué tipo de registro querés hacer hoy?",
            reply_markup=teclado,
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("marcar_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_marcado(call):
        import time

        if time.time() - call.message.date > 86400:  # 24 horas máximo
            bot.answer_callback_query(
                call.id, "❌ Este botón ha expirado.", show_alert=True
            )
            bot.edit_message_reply_markup(
                call.message.chat.id, call.message.message_id, reply_markup=None
            )
            return

        bot.answer_callback_query(call.id)
        modo = "directo" if call.data == "marcar_directo" else "normal"
        bot.edit_message_text(
            "⚙️ Comando recibido. Abriendo Google Sheets...",
            call.message.chat.id,
            call.message.message_id,
        )

        respuesta = gamma_app.agente_excel.ejecutar_marcado_para_bot(modo=modo)
        bot.edit_message_text(
            respuesta,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
        )

    @bot.message_handler(commands=["marcar_materia"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_marcar_materia(message):
        msg = bot.reply_to(message, "⚙️ Registrando asistencia en la materia actual...")
        resultado = gamma_app.agente_materias.marcar_asistencia()
        bot.edit_message_text(
            resultado, message.chat.id, msg.message_id, parse_mode="Markdown"
        )

    @bot.message_handler(commands=["cierre"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_cierre(message):
        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("✅ Confirmar", callback_data="cierre_confirmar"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cierre_cancelar"),
        )
        reply_with_expiration(
            bot,
            message.chat.id,
            "⚠️ *¿Ejecutar el cierre de período?*\n\n_Esta acción no se puede deshacer._",
            parse_mode="Markdown",
            reply_markup=teclado,
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_cierre(call):
        import time

        if time.time() - call.message.date > 86400:
            bot.answer_callback_query(
                call.id, "❌ Este botón ha expirado.", show_alert=True
            )
            bot.edit_message_reply_markup(
                call.message.chat.id, call.message.message_id, reply_markup=None
            )
            return

        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        if call.data == "cierre_cancelar":
            bot.edit_message_text("❌ Cierre cancelado.", chat_id, msg_id)
            return

        if call.data == "cierre_confirmar":
            bot.edit_message_text(
                "⚙️ Ejecutando cierre de período en Google Sheets...", chat_id, msg_id
            )
            respuesta = gamma_app.agente_excel.ejecutar_cierre_periodo_manual()
            bot.send_message(chat_id, respuesta, parse_mode="Markdown")

            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton(
                    "✅ Sí, aplicar descuento", callback_data="cierre_descuento_si"
                ),
                InlineKeyboardButton(
                    "❌ No, generar reporte directo",
                    callback_data="cierre_descuento_no",
                ),
            )
            reply_with_expiration(
                bot,
                chat_id,
                "¿Deseas aplicar algún **descuento** al salario calculado de este mes?",
                parse_mode="Markdown",
                reply_markup=teclado,
            )
            return

        if call.data == "cierre_descuento_no":
            bot.edit_message_text(
                "✅ Generando reporte sin descuentos...", chat_id, msg_id
            )
            generar_y_enviar_reporte(bot, gamma_app, call.message, descuento=0)
            return

        if call.data == "cierre_descuento_si":
            msg = bot.edit_message_text(
                "✍️ *Por favor, enviame el monto exacto a descontar.*\n"
                "Escribí sólo números (ej: `50000`).",
                chat_id,
                msg_id,
                parse_mode="Markdown",
            )
            bot.register_next_step_handler(
                msg, lambda m: capturar_monto_descuento(m, bot, gamma_app)
            )
            return

    @bot.message_handler(commands=["reporte"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_reporte(message):
        texto = message.text.lower()
        if "horas" in texto:
            iniciar_flujo_reporte_horas(message, bot, gamma_app)
        elif "finanzas" in texto or "diario" in texto:
            generar_y_enviar_reporte_financiero(bot, gamma_app, message)
        else:
            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton("⏱️ Horas", callback_data="reporte_tipo_horas"),
                InlineKeyboardButton(
                    "💰 Libro Diario", callback_data="reporte_tipo_finanzas"
                ),
            )
            reply_with_expiration(
                bot,
                message.chat.id,
                "📊 *¿Qué reporte deseas generar hoy?*",
                parse_mode="Markdown",
                reply_markup=teclado,
                reply_to_message_id=message.message_id,
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reporte_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_reporte(call):
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        data = call.data

        if data == "reporte_cancelar":
            bot.edit_message_text("❌ Operación cancelada.", chat_id, msg_id)
            return

        if data == "reporte_tipo_horas":
            iniciar_flujo_reporte_horas(call.message, bot, gamma_app, is_callback=True)
            return

        if data == "reporte_tipo_finanzas":
            generar_y_enviar_reporte_financiero(
                bot, gamma_app, call.message, is_callback=True
            )
            return

        if data.startswith("reporte_hoja_"):
            nombre_hoja = data[len("reporte_hoja_") :]
            EstadoGestor.set(f"reporte_{chat_id}", nombre_hoja)

            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton(
                    "✅ Sí, aplicar descuento", callback_data="reporte_desc_si"
                ),
                InlineKeyboardButton(
                    "❌ No, reporte directo", callback_data="reporte_desc_no"
                ),
            )
            bot.delete_message(chat_id, msg_id)
            reply_with_expiration(
                bot,
                chat_id,
                f"📅 Período seleccionado: *{nombre_hoja}*\n\n"
                f"¿Deseas aplicar algún *descuento* al salario calculado?",
                parse_mode="Markdown",
                reply_markup=teclado,
            )
            return

        if data == "reporte_desc_no":
            nombre_hoja = EstadoGestor.pop(f"reporte_{chat_id}")
            if not nombre_hoja:
                bot.edit_message_text(
                    "❌ Sesión expirada. Ejecutá /reporte de nuevo.", chat_id, msg_id
                )
                return
            bot.edit_message_text(
                "✅ Generando reporte sin descuentos...", chat_id, msg_id
            )
            generar_y_enviar_reporte_por_hoja(
                bot, gamma_app, call.message, nombre_hoja, descuento=0
            )
            return

        if data == "reporte_desc_si":
            msg = bot.edit_message_text(
                "✍️ *Ingresá el monto exacto a descontar.*\n"
                "Solo números (ej: `50000`).",
                chat_id,
                msg_id,
                parse_mode="Markdown",
            )
            bot.register_next_step_handler(
                msg, lambda m: capturar_descuento_reporte(m, bot, gamma_app)
            )
            return
