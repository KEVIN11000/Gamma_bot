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

    # --- GASTOS FIJOS (SOPORTE DUAL) ---
    def _enviar_menu_fijos(bot, chat_id):
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        datos = repo.obtener_gastos_fijos()
        gastos = datos["gastos"]
        total = datos["total"]

        texto = "📊 *GASTOS FIJOS MENSUALES (Presupuesto Base)*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        idx = 1
        for cat, items in gastos.items():
            for item in items:
                monto_str = (
                    f"₲ {item['monto']:,}".replace(",", ".")
                    if item["monto"]
                    else "[Sin asignar]"
                )
                texto += f"{idx}. {item['concepto']}: {monto_str}\n"
                idx += 1

        texto += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n💰 *Total Comprometido:* ₲ {total:,}".replace(
                ",", "."
            )
            + " / mes"
        )

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📊 1. Ver Desglose", callback_data="fijos_ver"),
            InlineKeyboardButton("✏️ 2. Modificar Monto", callback_data="fijos_editar"),
        )
        markup.row(
            InlineKeyboardButton("➕ 3. Registrar Nuevo", callback_data="fijos_nuevo"),
            InlineKeyboardButton("❌ Cerrar", callback_data="fijos_cerrar"),
        )

        bot.send_message(chat_id, texto, reply_markup=markup, parse_mode="Markdown")

    @bot.message_handler(commands=["fijos", "gastos_fijos"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_fijos_menu(message):
        _enviar_menu_fijos(bot, message.chat.id)

    @bot.message_handler(commands=["fijo_set"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_fijo_set(message):
        partes = message.text.split(maxsplit=2)
        if len(partes) < 3:
            bot.reply_to(message, "Uso: /fijo_set <Concepto> <Monto>")
            return
        concepto = partes[1]
        try:
            monto = int(partes[2].replace(".", "").replace(",", ""))
        except ValueError:
            bot.reply_to(message, "El monto debe ser un número entero.")
            return

        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        if repo.actualizar_monto_gasto_fijo(concepto, monto):
            bot.reply_to(
                message,
                f"✅ Monto de '{concepto}' actualizado a ₲ {monto:,}".replace(",", "."),
            )
        else:
            bot.reply_to(message, f"❌ No se encontró el concepto '{concepto}'.")

    @bot.message_handler(commands=["fijo_nuevo"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_fijo_nuevo(message):
        partes = message.text.split(maxsplit=1)
        if len(partes) < 2:
            bot.reply_to(
                message, "Uso: /fijo_nuevo <Categoria> | <Concepto> | <Monto> | [Obs]"
            )
            return

        segmentos = [s.strip() for s in partes[1].split("|")]
        if len(segmentos) < 3:
            bot.reply_to(message, "❌ Formato incorrecto. Separa los datos con '|'.")
            return

        categoria, concepto, monto_str = segmentos[0], segmentos[1], segmentos[2]
        obs = segmentos[3] if len(segmentos) > 3 else ""

        from logic.logic import safe_int

        monto = safe_int(monto_str)

        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        repo.agregar_gasto_fijo(categoria, concepto, monto, obs)
        bot.reply_to(
            message,
            f"✅ Nuevo gasto fijo registrado: {concepto} (₲ {monto:,})".replace(
                ",", "."
            ),
        )

    @bot.callback_query_handler(func=lambda c: c.data.startswith("fijos_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_fijos_callback(call):
        accion = call.data.replace("fijos_", "")
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()

        if accion == "cerrar":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return

        if accion == "ver":
            datos = repo.obtener_gastos_fijos()
            texto = "📊 *Desglose por Categoría*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for cat, items in datos["gastos"].items():
                texto += f"\n*Categoría: {cat}*\n"
                subtotal = 0
                for item in items:
                    subtotal += item["monto"]
                    texto += f" - {item['concepto']}: ₲ {item['monto']:,}\n".replace(
                        ",", "."
                    )
                texto += f" _Subtotal: ₲ {subtotal:,}_\n".replace(",", ".")
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("⬅️ Volver", callback_data="fijos_volver"))
            bot.edit_message_text(
                texto,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown",
            )

        elif accion == "volver":
            _enviar_menu_fijos(bot, call.message.chat.id)
            bot.delete_message(call.message.chat.id, call.message.message_id)

        elif accion == "editar":
            datos = repo.obtener_gastos_fijos()
            markup = InlineKeyboardMarkup()
            for cat, items in datos["gastos"].items():
                for item in items:
                    markup.add(
                        InlineKeyboardButton(
                            f"✏️ {item['concepto']}",
                            callback_data=f"fijos_sel_{item['concepto']}",
                        )
                    )
            markup.add(
                InlineKeyboardButton("❌ Cancelar", callback_data="fijos_cerrar")
            )
            bot.edit_message_text(
                "Selecciona el concepto que deseas modificar:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )

        elif accion.startswith("sel_"):
            concepto = accion.replace("sel_", "")
            set_state(call.from_user.id, "fijos_edit_monto", {"concepto": concepto})
            msg = bot.send_message(
                call.message.chat.id,
                f"Has seleccionado *{concepto}*.\nIngresa el nuevo monto en Guaraníes (o escribe /cancelar):",
                parse_mode="Markdown",
            )
            bot.register_next_step_handler(msg, _step_guardar_monto_fijo, concepto, bot)

        elif accion == "nuevo":
            markup = InlineKeyboardMarkup(row_width=2)
            cats = [
                "Servicios",
                "Educación",
                "Salud",
                "Movilidad",
                "Hogar/Alquiler",
                "Otro",
            ]
            botones = [
                InlineKeyboardButton(c, callback_data=f"fijos_ncat_{c}") for c in cats
            ]
            markup.add(*botones)
            markup.add(
                InlineKeyboardButton("❌ Cancelar", callback_data="fijos_cerrar")
            )
            bot.edit_message_text(
                "Selecciona la categoría para el nuevo gasto:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )

        elif accion.startswith("ncat_"):
            cat = accion.replace("ncat_", "")
            set_state(call.from_user.id, "fijos_nuevo_concepto", {"categoria": cat})
            msg = bot.send_message(
                call.message.chat.id,
                f"Categoría: *{cat}*.\nPor favor escribe el nombre o concepto del gasto (ej. Seguro Médico) o /cancelar:",
                parse_mode="Markdown",
            )
            bot.register_next_step_handler(msg, _step_guardar_nuevo_concepto, cat, bot)

    return True


def _step_guardar_monto_fijo(message, concepto, bot):
    if message.text.strip().lower() == "/cancelar":
        clear_state(message.from_user.id)
        bot.reply_to(message, "❌ Operación cancelada.")
        return

    from logic.logic import safe_int

    monto = safe_int(message.text)
    if monto == 0 and message.text.strip() != "0":
        msg = bot.reply_to(message, "❌ Monto inválido. Ingresa solo números.")
        bot.register_next_step_handler(msg, _step_guardar_monto_fijo, concepto, bot)
        return

    from repositories.sheets_repository import SheetsRepository

    repo = SheetsRepository()
    if repo.actualizar_monto_gasto_fijo(concepto, monto):
        bot.reply_to(
            message, f"✅ Se actualizó '{concepto}' a ₲ {monto:,}".replace(",", ".")
        )
    else:
        bot.reply_to(
            message, "❌ Hubo un error al actualizar (concepto no encontrado)."
        )
    clear_state(message.from_user.id)


def _step_guardar_nuevo_concepto(message, categoria, bot):
    if message.text.strip().lower() == "/cancelar":
        clear_state(message.from_user.id)
        bot.reply_to(message, "❌ Operación cancelada.")
        return

    concepto = message.text.strip()
    state = get_state(message.from_user.id) or {}
    state["concepto"] = concepto
    set_state(message.from_user.id, "fijos_nuevo_monto", state)

    msg = bot.reply_to(
        message,
        f"Concepto: *{concepto}*.\nAhora ingresa el monto mensual en ₲:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, _step_guardar_nuevo_monto, bot)


def _step_guardar_nuevo_monto(message, bot):
    if message.text.strip().lower() == "/cancelar":
        clear_state(message.from_user.id)
        bot.reply_to(message, "❌ Operación cancelada.")
        return

    from logic.logic import safe_int

    monto = safe_int(message.text)
    if monto == 0 and message.text.strip() != "0":
        msg = bot.reply_to(message, "❌ Monto inválido. Ingresa solo números.")
        bot.register_next_step_handler(msg, _step_guardar_nuevo_monto, bot)
        return

    state = get_state(message.from_user.id)
    if not state:
        return

    from repositories.sheets_repository import SheetsRepository

    repo = SheetsRepository()
    repo.agregar_gasto_fijo(state["categoria"], state["concepto"], monto, "")
    bot.reply_to(
        message,
        f"✅ Gasto '{state['concepto']}' de ₲ {monto:,} guardado exitosamente.".replace(
            ",", "."
        ),
    )
    clear_state(message.from_user.id)
