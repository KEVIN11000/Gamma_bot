import os
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logger_config import setup_logger
from com.core.security import auth_required
from com.core.errors import safe_handler
from com.core.security import verificar_usuario_manual
from logic.logic import EstadoGestor
from logic.pdf_service import PDFService

logger = setup_logger("asistencia_handler")

def register_asistencia_handlers(bot: TeleBot, gamma_app):
    
    @bot.message_handler(commands=['marcar'])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_marcar(message):
        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("▶️ Marcar",         callback_data="marcar_normal"),
            InlineKeyboardButton("🚪 Salida directa", callback_data="marcar_directo"),
        )
        bot.send_message(message.chat.id, "¿Qué tipo de registro querés hacer hoy?", reply_markup=teclado)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("marcar_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_marcado(call):
        import time
        if time.time() - call.message.date > 86400: # 24 horas máximo
            bot.answer_callback_query(call.id, "❌ Este botón ha expirado.", show_alert=True)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            return

        bot.answer_callback_query(call.id)
        modo = "directo" if call.data == "marcar_directo" else "normal"
        bot.edit_message_text("⚙️ Comando recibido. Abriendo Google Sheets...", call.message.chat.id, call.message.message_id)

        respuesta = gamma_app.agente_excel.ejecutar_marcado_para_bot(modo=modo)
        bot.edit_message_text(respuesta, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    @bot.message_handler(commands=['marcar_materia'])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_marcar_materia(message):
        msg = bot.reply_to(message, "⚙️ Registrando asistencia en la materia actual...")
        resultado = gamma_app.agente_materias.marcar_asistencia()
        bot.edit_message_text(resultado, message.chat.id, msg.message_id, parse_mode="Markdown")

    @bot.message_handler(commands=['cierre'])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_cierre(message):
        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("✅ Confirmar", callback_data="cierre_confirmar"),
            InlineKeyboardButton("❌ Cancelar",  callback_data="cierre_cancelar"),
        )
        bot.send_message(message.chat.id, "⚠️ *¿Ejecutar el cierre de período?*\n\n_Esta acción no se puede deshacer._", parse_mode="Markdown", reply_markup=teclado)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_cierre(call):
        import time
        if time.time() - call.message.date > 86400:
            bot.answer_callback_query(call.id, "❌ Este botón ha expirado.", show_alert=True)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            return

        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        if call.data == "cierre_cancelar":
            bot.edit_message_text("❌ Cierre cancelado.", chat_id, msg_id)
            return

        if call.data == "cierre_confirmar":
            bot.edit_message_text("⚙️ Ejecutando cierre de período en Google Sheets...", chat_id, msg_id)
            respuesta = gamma_app.agente_excel.ejecutar_cierre_periodo_manual()
            bot.send_message(chat_id, respuesta, parse_mode="Markdown")

            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton("✅ Sí, aplicar descuento", callback_data="cierre_descuento_si"),
                InlineKeyboardButton("❌ No, generar reporte directo", callback_data="cierre_descuento_no"),
            )
            bot.send_message(
                chat_id,
                "¿Deseas aplicar algún **descuento** al salario calculado de este mes?",
                parse_mode="Markdown",
                reply_markup=teclado
            )
            return

        if call.data == "cierre_descuento_no":
            bot.edit_message_text("✅ Generando reporte sin descuentos...", chat_id, msg_id)
            _generar_y_enviar_reporte(bot, gamma_app, call.message, descuento=0)
            return

        if call.data == "cierre_descuento_si":
            msg = bot.edit_message_text(
                "✍️ *Por favor, enviame el monto exacto a descontar.*\n"
                "Escribí sólo números (ej: `50000`).",
                chat_id,
                msg_id,
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, lambda m: _capturar_monto_descuento(m, bot, gamma_app))
            return

    @bot.message_handler(commands=['reporte'])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_reporte(message):
        texto = message.text.lower()
        if "horas" in texto:
            _iniciar_flujo_reporte_horas(message, bot, gamma_app)
        elif "finanzas" in texto or "diario" in texto:
            _generar_y_enviar_reporte_financiero(bot, gamma_app, message)
        else:
            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton("⏱️ Horas", callback_data="reporte_tipo_horas"),
                InlineKeyboardButton("💰 Libro Diario", callback_data="reporte_tipo_finanzas")
            )
            bot.reply_to(
                message,
                "📊 *¿Qué reporte deseas generar hoy?*",
                parse_mode="Markdown",
                reply_markup=teclado
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reporte_"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_reporte(call):
        bot.answer_callback_query(call.id)
        chat_id  = call.message.chat.id
        msg_id   = call.message.message_id
        data     = call.data

        if data == "reporte_cancelar":
            bot.edit_message_text("❌ Operación cancelada.", chat_id, msg_id)
            return
            
        if data == "reporte_tipo_horas":
            _iniciar_flujo_reporte_horas(call.message, bot, gamma_app, is_callback=True)
            return

        if data == "reporte_tipo_finanzas":
            _generar_y_enviar_reporte_financiero(bot, gamma_app, call.message, is_callback=True)
            return

        if data.startswith("reporte_hoja_"):
            nombre_hoja = data[len("reporte_hoja_"):]
            EstadoGestor.set(f"reporte_{chat_id}", nombre_hoja)

            teclado = InlineKeyboardMarkup()
            teclado.row(
                InlineKeyboardButton("✅ Sí, aplicar descuento",    callback_data="reporte_desc_si"),
                InlineKeyboardButton("❌ No, reporte directo",       callback_data="reporte_desc_no"),
            )
            bot.edit_message_text(
                f"📅 Período seleccionado: *{nombre_hoja}*\n\n"
                f"¿Deseas aplicar algún *descuento* al salario calculado?",
                chat_id, msg_id,
                parse_mode="Markdown",
                reply_markup=teclado
            )
            return

        if data == "reporte_desc_no":
            nombre_hoja = EstadoGestor.pop(f"reporte_{chat_id}")
            if not nombre_hoja:
                bot.edit_message_text("❌ Sesión expirada. Ejecutá /reporte de nuevo.", chat_id, msg_id)
                return
            bot.edit_message_text("✅ Generando reporte sin descuentos...", chat_id, msg_id)
            _generar_y_enviar_reporte_por_hoja(bot, gamma_app, call.message, nombre_hoja, descuento=0)
            return

        if data == "reporte_desc_si":
            msg = bot.edit_message_text(
                "✍️ *Ingresá el monto exacto a descontar.*\n"
                "Solo números (ej: `50000`).",
                chat_id, msg_id,
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, lambda m: _capturar_descuento_reporte(m, bot, gamma_app))
            return


# --- Funciones auxiliares
def _iniciar_flujo_reporte_horas(message, bot, gamma_app, is_callback=False):
    nombres = gamma_app.agente_excel.obtener_nombres_hojas(limite=6)

    if not nombres:
        msj = "❌ No hay períodos anteriores disponibles para generar un reporte."
        if is_callback:
            bot.edit_message_text(msj, message.chat.id, message.message_id)
        else:
            bot.reply_to(message, msj)
        return

    teclado = InlineKeyboardMarkup()
    for nombre in nombres:
        safe = nombre[:30]
        teclado.row(InlineKeyboardButton(f"📅 {nombre}", callback_data=f"reporte_hoja_{safe}"))
    teclado.row(InlineKeyboardButton("❌ Cancelar", callback_data="reporte_cancelar"))

    texto = "📄 *¿De qué período querés el reporte de HORAS?*\n_Se muestran los últimos períodos cerrados._"
    if is_callback:
        bot.edit_message_text(texto, message.chat.id, message.message_id, parse_mode="Markdown", reply_markup=teclado)
    else:
        bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=teclado)


def _generar_y_enviar_reporte_financiero(bot, gamma_app, message_obj, is_callback=False):
    chat_id = message_obj.chat.id
    msg_id = message_obj.message_id
    
    if is_callback:
        bot.edit_message_text("📄 Procesando datos financieros y armando PDF...", chat_id, msg_id)
    else:
        bot.send_message(chat_id, "📄 Procesando datos financieros y armando PDF...")
        
    datos, error = gamma_app.agente_financiero.preparar_datos_reporte()
    
    if error:
        bot.send_message(chat_id, error)
        return
        
    from logic.pdf_service import PDFService
    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)

    if ruta_pdf:
        with open(ruta_pdf, 'rb') as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"📊 {msg_pdf}",
                visible_file_name=os.path.basename(ruta_pdf)
            )
    else:
        bot.send_message(chat_id, msg_pdf)


def _capturar_monto_descuento(message, bot, gamma_app):
    if not verificar_usuario_manual(bot, message): return
    if not message.text:
        bot.reply_to(message, "❌ Por favor, enviá un texto con el número. (No se admiten stickers ni imágenes)")
        return
        
    try:
        texto_ingresado = message.text.strip().replace(".", "").replace(",", "")
        monto_descuento = float(texto_ingresado)
        _generar_y_enviar_reporte(bot, gamma_app, message, descuento=monto_descuento)
    except ValueError:
        bot.reply_to(
            message,
            "❌ *Error:* El monto debe ser numérico.\n"
            "Operación de reporte abortada. Podés pedir el reporte de nuevo más tarde o cerrar otro ciclo.",
            parse_mode="Markdown"
        )

def _generar_y_enviar_reporte(bot, gamma_app, message_obj, descuento):
    bot.send_message(message_obj.chat.id, "📄 Procesando datos y armando PDF de horas...")
    
    datos, error = gamma_app.agente_excel.preparar_datos_reporte(descuento=descuento)
    if error:
        bot.send_message(message_obj.chat.id, error)
        return
        
    from logic.pdf_service import PDFService
    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)

    if ruta_pdf:
        with open(ruta_pdf, 'rb') as f:
            bot.send_document(
                message_obj.chat.id,
                f,
                caption=f"📊 {msg_pdf}",
                visible_file_name=os.path.basename(ruta_pdf)
            )
    else:
        bot.send_message(message_obj.chat.id, msg_pdf)

def _capturar_descuento_reporte(message, bot, gamma_app):
    if not verificar_usuario_manual(bot, message): return
    if not message.text:
        bot.reply_to(message, "❌ Por favor, enviá un texto numérico. (No se admiten archivos)")
        return
        
    try:
        chat_id = message.chat.id
        nombre_hoja = EstadoGestor.pop(f"reporte_{chat_id}")
        if not nombre_hoja:
            bot.reply_to(message, "❌ Sesión expirada. Ejecutá /reporte de nuevo.")
            return
        monto = float(message.text.strip().replace(".", "").replace(",", ""))
        _generar_y_enviar_reporte_por_hoja(bot, gamma_app, message, nombre_hoja, descuento=monto)
    except ValueError:
        bot.reply_to(
            message,
            "❌ El monto debe ser numérico. Operación cancelada.\n"
            "Ejecutá /reporte para intentar de nuevo."
        )

def _generar_y_enviar_reporte_por_hoja(bot, gamma_app, message_obj, nombre_hoja: str, descuento: float):
    bot.send_message(message_obj.chat.id, "📄 Procesando datos y armando PDF de horas...")
    
    datos, error = gamma_app.agente_excel.preparar_datos_reporte(nombre_hoja=nombre_hoja, descuento=descuento)
    if error:
        bot.send_message(message_obj.chat.id, error)
        return
        
    from logic.pdf_service import PDFService
    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)
    
    if ruta_pdf:
        with open(ruta_pdf, 'rb') as f:
            bot.send_document(
                message_obj.chat.id,
                f,
                caption=f"📊 {msg_pdf}",
                visible_file_name=os.path.basename(ruta_pdf)
            )
    else:
        bot.send_message(message_obj.chat.id, msg_pdf)
