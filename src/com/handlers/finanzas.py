from __future__ import annotations

from typing import Any

from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from com.core.utils import reply_with_expiration

from com.core.errors import safe_handler
from com.core.security import auth_required
from com.core.states import set_state, get_state, clear_state
from com.utils.validators import parse_monto
from app_queue.worker import enqueue
import datetime

from logger_config import setup_logger
from logic.ai_service import AIService
from logic.logic import EstadoGestor

logger = setup_logger("finanzas_handler")


def register_finanzas_handlers(bot: TeleBot, gamma_app: Any) -> Any:

    @bot.message_handler(commands=["gasto", "ingreso"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_movimiento_financiero(message):
        comando = message.text.split()[0].replace("/", "").lower()
        tipo_mov = "Gasto" if comando == "gasto" else "Ingreso"

        partes = message.text.split(maxsplit=1)
        if len(partes) < 2:
            user_id = message.from_user.id
            set_state(user_id, f"{comando}_paso1", {"tipo_movimiento": tipo_mov})
            if tipo_mov == "Gasto":
                bot.reply_to(
                    message, "💸 ¿Cuánto fue el gasto? (Ingresa el monto en Gs.)"
                )
            else:
                bot.reply_to(
                    message, "💰 ¿Cuánto fue el ingreso? (Ingresa el monto en Gs.)"
                )
            return

        # Modo Directo (Express)
        texto_usuario = partes[1]
        msg_carga = bot.reply_to(message, f"⏳ Procesando {tipo_mov.lower()} con IA...")

        datos = AIService.procesar_movimiento_con_ia(
            texto_usuario, tipo_movimiento=tipo_mov
        )
        if "error" in datos:
            bot.edit_message_text(
                f"❌ Error: {datos['error']}", message.chat.id, msg_carga.message_id
            )
            return

        resultado = gamma_app.agente_financiero.registrar_movimiento(datos)
        bot.edit_message_text(resultado, message.chat.id, msg_carga.message_id)

    @bot.message_handler(
        func=lambda m: bool(get_state(m.from_user.id))
        and (get_state(m.from_user.id) or {}).get("estado")
        in ["gasto_paso1", "ingreso_paso1"]
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_paso1(message):
        if message.text.strip().lower() == "/cancelar":
            clear_state(message.from_user.id)
            bot.reply_to(message, "❌ Operación cancelada.")
            return

        user_id = message.from_user.id
        state = get_state(user_id)
        if not state:
            return
        datos = state["datos"]
        tipo = datos["tipo_movimiento"]

        try:
            monto = parse_monto(message.text)
        except ValueError:
            bot.reply_to(
                message, "❌ Por favor, ingresa un monto válido (sólo números)."
            )
            return

        datos["total"] = monto
        datos["neto"] = monto
        datos["iva"] = 0

        markup = InlineKeyboardMarkup()
        if tipo == "Gasto":
            set_state(user_id, "gasto_paso2", datos)
            markup.row(
                InlineKeyboardButton(
                    "🛒 Alimentación", callback_data="cat_gasto_Alimentación"
                ),
                InlineKeyboardButton(
                    "🚌 Transporte", callback_data="cat_gasto_Transporte"
                ),
            )
            markup.row(
                InlineKeyboardButton("🏠 Hogar", callback_data="cat_gasto_Hogar"),
                InlineKeyboardButton("💊 Salud", callback_data="cat_gasto_Salud"),
            )
            markup.row(
                InlineKeyboardButton(
                    "📚 Educación", callback_data="cat_gasto_Educación"
                ),
                InlineKeyboardButton("🔧 Otros", callback_data="cat_gasto_Otros"),
            )
            bot.reply_to(message, "📋 ¿A qué categoría pertenece?", reply_markup=markup)
        else:
            set_state(user_id, "ingreso_paso2", datos)
            markup.row(
                InlineKeyboardButton("💼 Salario", callback_data="cat_ingreso_Salario"),
                InlineKeyboardButton("🤝 Cliente", callback_data="cat_ingreso_Cliente"),
            )
            markup.row(
                InlineKeyboardButton(
                    "📈 Inversión", callback_data="cat_ingreso_Inversión"
                ),
                InlineKeyboardButton("🔧 Otros", callback_data="cat_ingreso_Otros"),
            )
            bot.reply_to(message, "📋 ¿Categoría?", reply_markup=markup)

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("cat_gasto_")
        or call.data.startswith("cat_ingreso_")
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_categoria(call):
        user_id = call.from_user.id
        state = get_state(user_id)
        if not state or state.get("estado") not in ["gasto_paso2", "ingreso_paso2"]:
            bot.answer_callback_query(
                call.id, "Operación expirada o inválida.", show_alert=True
            )
            return

        bot.answer_callback_query(call.id)
        datos = state["datos"]
        cat = call.data.split("_", 2)[2]
        datos["categoria"] = cat
        tipo = datos["tipo_movimiento"]

        if tipo == "Gasto":
            set_state(user_id, "gasto_paso3", datos)
            bot.edit_message_text(
                "🧾 ¿Tiene número de factura? Escríbelo o escribe S/N",
                call.message.chat.id,
                call.message.message_id,
            )
        else:
            set_state(user_id, "ingreso_paso3", datos)
            bot.edit_message_text(
                "🧾 ¿Número de recibo? (o S/N)",
                call.message.chat.id,
                call.message.message_id,
            )

    @bot.message_handler(
        func=lambda m: bool(get_state(m.from_user.id))
        and (get_state(m.from_user.id) or {}).get("estado")
        in ["gasto_paso3", "ingreso_paso3"]
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_paso3(message):
        if message.text.strip().lower() == "/cancelar":
            clear_state(message.from_user.id)
            bot.reply_to(message, "❌ Operación cancelada.")
            return

        user_id = message.from_user.id
        chat_id = message.chat.id
        state = get_state(user_id)
        if not state:
            return
        datos = state["datos"]
        tipo = datos["tipo_movimiento"]

        factura_str = message.text.strip()
        if factura_str.lower() in ["s/n", "sn", "no"]:
            factura_str = "S/N"

        now = datetime.datetime.now()
        meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        payload = {
            "tipo_movimiento": tipo,
            "total": datos["total"],
            "neto": datos["neto"],
            "iva": datos["iva"],
            "categoria": datos["categoria"],
            "nro_factura": factura_str,
            "fecha": now.strftime("%d/%m/%Y"),
            "mes": meses[now.month - 1],
            "proveedor_cliente": "",
            "comprobante": "Factura" if tipo == "Gasto" else "Recibo",
            "file_id": "",
        }

        enqueue(chat_id, "registrar_movimiento", payload)
        clear_state(user_id)

        if tipo == "Gasto":
            bot.reply_to(
                message, "⏳ Guardando tu gasto... te avisaré cuando esté listo."
            )
        else:
            bot.reply_to(
                message, "⏳ Guardando tu ingreso... te avisaré cuando esté listo."
            )

    @bot.message_handler(commands=["balance"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_balance(message):
        balance_data = gamma_app.agente_financiero.obtener_balance()
        if not balance_data:
            bot.reply_to(message, "❌ No se pudo calcular el balance.")
            return

        ingresos = "{:,}".format(balance_data["ingresos"]).replace(",", ".")
        gastos = "{:,}".format(balance_data["gastos"]).replace(",", ".")
        neto = "{:,}".format(balance_data["flujo_neto"]).replace(",", ".")

        emoji_neto = "🟢" if balance_data["flujo_neto"] >= 0 else "🔴"

        msg = (
            "⚖️ *Balance General (Libro Diario)*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Ingresos Totales: Gs. {ingresos}\n"
            f"📉 Gastos Totales: Gs. {gastos}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"{emoji_neto} *Flujo Neto: Gs. {neto}*"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")

    @bot.message_handler(content_types=["photo"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def manejar_foto_ticket(message):
        msg_carga = bot.reply_to(
            message, "⏳ Descargando y analizando imagen con OCR (Gemini 2.5)..."
        )

        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            datos = AIService.analizar_ticket_con_ia(
                downloaded_file, mime_type="image/jpeg"
            )

            if "error" in datos:
                bot.edit_message_text(
                    f"❌ Error: {datos['error']}", message.chat.id, msg_carga.message_id
                )
                return

            datos["file_id"] = message.photo[-1].file_id

            cache_key = f"ocr_{msg_carga.message_id}"
            EstadoGestor.set(cache_key, datos)

            neto = "{:,}".format(
                gamma_app.agente_financiero.limpiar_monto(datos.get("neto", 0))
            ).replace(",", ".")
            iva = "{:,}".format(
                gamma_app.agente_financiero.limpiar_monto(datos.get("iva", 0))
            ).replace(",", ".")
            total = "{:,}".format(
                gamma_app.agente_financiero.limpiar_monto(datos.get("total", 0))
            ).replace(",", ".")

            texto_confirmacion = (
                "🧾 *Ticket Analizado*\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏢 *Proveedor:* {datos.get('proveedor_cliente')}\n"
                f"📄 *Factura:* {datos.get('nro_factura')}\n"
                f"💰 *Neto:* Gs. {neto}\n"
                f"⚖️ *IVA:* Gs. {iva}\n"
                f"💵 *Total:* Gs. {total}\n"
                f"🏷 *Categoría:* {datos.get('categoria')}\n"
                f"📝 *Tipo:* {datos.get('comprobante')}\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "¿Deseas guardar este gasto?"
            )

            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton(
                    "✅ Confirmar", callback_data=f"ocr_ok_{msg_carga.message_id}"
                ),
                InlineKeyboardButton(
                    "❌ Cancelar", callback_data=f"ocr_no_{msg_carga.message_id}"
                ),
            )

            bot.delete_message(message.chat.id, msg_carga.message_id)
            reply_with_expiration(
                bot,
                message.chat.id,
                texto_confirmacion,
                parse_mode="Markdown",
                reply_markup=teclado,
            )

        except Exception as e:
            logger.error(f"❌ Error procesando foto OCR: {e}")
            bot.edit_message_text(
                f"❌ Hubo un problema al procesar la imagen: {e}",
                message.chat.id,
                msg_carga.message_id,
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ocr_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_ocr(call):
        try:
            bot.answer_callback_query(call.id)
            _, accion, msg_id = call.data.split("_")
            cache_key = f"ocr_{msg_id}"

            if accion == "no":
                EstadoGestor.pop(cache_key)
                bot.edit_message_text(
                    "❌ Gasto descartado.",
                    call.message.chat.id,
                    call.message.message_id,
                )
                return

            if accion == "ok":
                datos = EstadoGestor.pop(cache_key)
                if not datos:
                    bot.answer_callback_query(
                        call.id,
                        "❌ Este ticket ya fue procesado o ha expirado.",
                        show_alert=True,
                    )
                    bot.edit_message_reply_markup(
                        call.message.chat.id, call.message.message_id, reply_markup=None
                    )
                    return

                bot.edit_message_text(
                    "⏳ Guardando en Libro Diario...",
                    call.message.chat.id,
                    call.message.message_id,
                )
                resultado = gamma_app.agente_financiero.registrar_movimiento(datos)
                bot.edit_message_text(
                    resultado, call.message.chat.id, call.message.message_id
                )

        except Exception as e:
            logger.error(f"❌ Error en callback OCR: {e}")
            bot.send_message(call.message.chat.id, f"❌ Error interno OCR: {str(e)}")
