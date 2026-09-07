from __future__ import annotations

from typing import Any

import telebot
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from src.com.core.utils import reply_with_expiration

from src.com.core.errors import safe_handler
from src.com.core.security import auth_required, verificar_usuario_manual
from src.logger_config import setup_logger
from src.logic.ai_service import AIService
from src.logic.logic import EstadoGestor

logger = setup_logger("avisos_handler")


def register_avisos_handlers(bot: TeleBot, gamma_app: Any) -> Any:

    @bot.message_handler(commands=["aviso"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_aviso(message):
        partes = message.text.split(maxsplit=1)
        if len(partes) > 1:
            _procesar_frase_aviso(message, partes[1], bot, gamma_app)
        else:
            msg = bot.reply_to(
                message,
                "✍️ *Por favor, escribí qué querés agendar.*\n"
                "Ejemplo: `entregar el laboratorio de mecatrónica mañana a las 4 y media`",
                parse_mode="Markdown",
            )
            bot.register_next_step_handler(
                msg, lambda m: _capturar_frase_aviso_secuencial(m, bot, gamma_app)
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("aviso_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_aviso(call):
        try:
            bot.answer_callback_query(call.id)
            chat_id = call.message.chat.id

            if call.data == "aviso_cancelar":
                EstadoGestor.pop(chat_id)
                bot.edit_message_text(
                    "❌ Registro de aviso cancelado.", chat_id, call.message.message_id
                )
                return

            datos_evento = EstadoGestor.get(chat_id)

            if not datos_evento:
                bot.edit_message_text(
                    "❌ Error: Expiró la sesión del aviso. Por favor, intentá de nuevo.",
                    chat_id,
                    call.message.message_id,
                )
                return

            bot.edit_message_text(
                "💾 Escribiendo en la base de datos de Google Sheets...",
                chat_id,
                call.message.message_id,
            )
            resultado_escritura = gamma_app.agente_excel.guardar_aviso_calendar(
                datos_evento
            )
            EstadoGestor.pop(chat_id)
            bot.edit_message_text(
                resultado_escritura,
                chat_id,
                call.message.message_id,
                parse_mode="Markdown",
            )

        except Exception as e:
            bot.send_message(
                call.message.chat.id, f"❌ Error al procesar confirmación: {str(e)}"
            )

    @bot.message_handler(commands=["avisos"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_avisos(message):
        user = message.from_user
        logger.info(f"[/avisos] Panel de gestión solicitado por ID: {user.id}")
        try:
            lista_avisos = gamma_app.agente_excel.obtener_lista_avisos_calendar()

            if not lista_avisos:
                bot.reply_to(
                    message, "📭 No tenés ningún aviso programado en este momento."
                )
                return

            texto = "📋 *TUS RECORDATORIOS ACTIVOS*\n━━━━━━━━━━━━━━━━━━━━━\n"
            teclado = InlineKeyboardMarkup()
            botones_fila = []

            for idx, aviso in enumerate(lista_avisos):
                texto += f"*{idx + 1}.* ⏳ *{aviso['titulo']}*\n    📅 {aviso['fecha_evento']} hs.\n\n"

                btn = InlineKeyboardButton(
                    f"❌ Borrar {idx + 1}", callback_data=f"borrar_{idx}"
                )
                botones_fila.append(btn)

                if len(botones_fila) == 2:
                    teclado.row(*botones_fila)
                    botones_fila = []

            if botones_fila:
                teclado.row(*botones_fila)

            texto += "━━━━━━━━━━━━━━━━━━━━━\n_¿Querés eliminar alguno? Tocá el botón correspondiente._"
            reply_with_expiration(bot, message.chat.id, texto, parse_mode="Markdown", reply_markup=teclado, reply_to_message_id=message.message_id)

        except telebot.apihelper.ApiTelegramException as tel_e:
            logger.error(f"⚠️ Error de red/API en Telegram: {str(tel_e)}")
            bot.reply_to(
                message,
                "⚠️ No pude enviarte la lista por un error de conexión con Telegram.",
            )
        except Exception as e:
            logger.error(f"❌ Error en comando_avisos: {str(e)}")
            bot.reply_to(message, f"❌ Error al cargar el panel de avisos: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("borrar_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_borrar_aviso(call):
        try:
            bot.answer_callback_query(call.id)
            chat_id = call.message.chat.id
            msg_id = call.message.message_id

            indice = int(call.data.split("_")[1])
            lista_avisos_actual = gamma_app.agente_excel.obtener_lista_avisos_calendar()

            if 0 <= indice < len(lista_avisos_actual):
                evento_a_borrar = lista_avisos_actual[indice]
                exito = gamma_app.agente_excel.eliminar_aviso_calendar(
                    evento_a_borrar["id"]
                )

                if exito:
                    bot.send_message(
                        chat_id,
                        f"🗑️ El aviso *'{evento_a_borrar['titulo']}'* fue eliminado correctamente.",
                        parse_mode="Markdown",
                    )
                else:
                    bot.send_message(
                        chat_id, "❌ Hubo un error al eliminar el evento de Calendar."
                    )
            else:
                bot.send_message(chat_id, "❌ El aviso seleccionado ya no existe.")

            lista_avisos = gamma_app.agente_excel.obtener_lista_avisos_calendar()
            if not lista_avisos:
                bot.edit_message_text(
                    "📭 No te quedan más avisos programados.", chat_id, msg_id
                )
                return

            texto = "📋 *TUS RECORDATORIOS ACTIVOS*\n━━━━━━━━━━━━━━━━━━━━━\n"
            teclado = InlineKeyboardMarkup()
            botones_fila = []

            for idx, aviso in enumerate(lista_avisos):
                texto += f"*{idx + 1}.* ⏳ *{aviso['titulo']}*\n    📅 {aviso['fecha_evento']} hs.\n\n"
                btn = InlineKeyboardButton(
                    f"❌ Borrar {idx + 1}", callback_data=f"borrar_{idx}"
                )
                botones_fila.append(btn)
                if len(botones_fila) == 2:
                    teclado.row(*botones_fila)
                    botones_fila = []
            if botones_fila:
                teclado.row(*botones_fila)

            texto += "━━━━━━━━━━━━━━━━━━━━━\n_¿Querés eliminar alguno? Tocá el botón correspondiente._"
            bot.delete_message(chat_id, msg_id)
            reply_with_expiration(
                bot, chat_id, texto, parse_mode="Markdown", reply_markup=teclado
            )

        except Exception as e:
            bot.send_message(
                call.message.chat.id,
                f"❌ Error al procesar la baja del aviso: {str(e)}",
            )


def _capturar_frase_aviso_secuencial(message: Any, bot: Any, gamma_app: Any) -> Any:
    if not verificar_usuario_manual(bot, message):
        return

    if not message.text or message.text.startswith("/"):
        bot.reply_to(message, "❌ Operación cancelada. No enviaste una frase válida.")
        return
    _procesar_frase_aviso(message, message.text, bot, gamma_app)


def _procesar_frase_aviso(message: Any, frase: str, bot: Any, gamma_app: Any) -> Any:
    msg_espera = bot.send_message(message.chat.id, "🧠 Analizando frase con Gemini...")
    datos_ia = AIService.interpretar_frase_con_ia(frase)

    if "error" in datos_ia:
        bot.edit_message_text(
            f"❌ {datos_ia['error']}", message.chat.id, msg_espera.message_id
        )
        return

    EstadoGestor.set(message.chat.id, datos_ia)

    teclado = InlineKeyboardMarkup()
    teclado.row(
        InlineKeyboardButton("✅ Guardar Aviso", callback_data="aviso_confirmar"),
        InlineKeyboardButton("❌ Cancelar", callback_data="aviso_cancelar"),
    )

    tarjeta_previsualizacion = (
        f"📋 *Previsualización del Aviso:*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Título:* {datos_ia['titulo']}\n"
        f"📅 *Fecha:* {datos_ia['fecha']}\n"
        f"⏰ *Hora:* {datos_ia['hora']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Los datos son correctos?"
    )

    bot.delete_message(message.chat.id, msg_espera.message_id)
    reply_with_expiration(
        bot,
        message.chat.id,
        tarjeta_previsualizacion,
        parse_mode="Markdown",
        reply_markup=teclado,
    )
