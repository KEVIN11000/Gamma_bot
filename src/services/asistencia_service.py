from pathlib import Path
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from com.core.security import verificar_usuario_manual
from logic.logic import EstadoGestor
from logic.pdf_service import PDFService


def iniciar_flujo_reporte_horas(
    message: Message, bot: TeleBot, gamma_app: "GammaApp", is_callback: bool = False
) -> None:
    """
    iniciar_flujo_reporte_horas method/function.

    Args:
        message: Description for message.
        bot: Description for bot.
        gamma_app: Description for gamma_app.
        is_callback: Description for is_callback.

    Returns:
        Description of the return value.

    Raises:
        Exception: Description of the exception.
    """
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
        teclado.row(
            InlineKeyboardButton(f"📅 {nombre}", callback_data=f"reporte_hoja_{safe}")
        )
    teclado.row(InlineKeyboardButton("❌ Cancelar", callback_data="reporte_cancelar"))

    texto = "📄 *¿De qué período querés el reporte de HORAS?*\n_Se muestran los últimos períodos cerrados._"
    if is_callback:
        bot.edit_message_text(
            texto,
            message.chat.id,
            message.message_id,
            parse_mode="Markdown",
            reply_markup=teclado,
        )
    else:
        bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=teclado)


def generar_y_enviar_reporte_financiero(
    bot: TeleBot, gamma_app: "GammaApp", message_obj: Message, is_callback: bool = False
) -> None:
    """
    generar_y_enviar_reporte_financiero method/function.

    Args:
        bot: Description for bot.
        gamma_app: Description for gamma_app.
        message_obj: Description for message_obj.
        is_callback: Description for is_callback.

    Returns:
        Description of the return value.

    Raises:
        Exception: Description of the exception.
    """
    chat_id = message_obj.chat.id
    msg_id = message_obj.message_id

    if is_callback:
        bot.edit_message_text(
            "📄 Procesando datos financieros y armando PDF...", chat_id, msg_id
        )
    else:
        bot.send_message(chat_id, "📄 Procesando datos financieros y armando PDF...")

    datos, error = gamma_app.agente_financiero.preparar_datos_reporte()

    if error:
        bot.send_message(chat_id, error)
        return

    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)

    if ruta_pdf:
        with open(ruta_pdf, "rb") as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"📊 {msg_pdf}",
                visible_file_name=Path(ruta_pdf).name,
            )
    else:
        bot.send_message(chat_id, msg_pdf)


def capturar_monto_descuento(
    message: Message, bot: TeleBot, gamma_app: "GammaApp"
) -> None:
    """
    capturar_monto_descuento method/function.

    Args:
        message: Description for message.
        bot: Description for bot.
        gamma_app: Description for gamma_app.

    Returns:
        Description of the return value.

    Raises:
        Exception: Description of the exception.
    """
    if not verificar_usuario_manual(bot, message):
        return
    if not message.text:
        bot.reply_to(
            message,
            "❌ Por favor, enviá un texto con el número. (No se admiten stickers ni imágenes)",
        )
        return

    try:
        texto_ingresado = message.text.strip().replace(".", "").replace(",", "")
        monto_descuento = float(texto_ingresado)
        incluir_iva = EstadoGestor.pop(f"iva_{message.chat.id}", False)
        generar_y_enviar_reporte(bot, gamma_app, message, descuento=monto_descuento, incluir_iva=incluir_iva)
    except ValueError:
        bot.reply_to(
            message,
            "❌ *Error:* El monto debe ser numérico.\n"
            "Operación de reporte abortada. Podés pedir el reporte de nuevo más tarde o cerrar otro ciclo.",
            parse_mode="Markdown",
        )


def generar_y_enviar_reporte(
    bot: TeleBot, gamma_app: "GammaApp", message_obj: Message, descuento: float, incluir_iva: bool = False
) -> None:
    """
    generar_y_enviar_reporte method/function.

    Args:
        bot: Description for bot.
        gamma_app: Description for gamma_app.
        message_obj: Description for message_obj.
        descuento: Description for descuento.
        incluir_iva: Si se debe incluir IVA en el reporte.

    Returns:
        Description of the return value.

    Raises:
        Exception: Description of the exception.
    """
    bot.send_message(
        message_obj.chat.id, "📄 Procesando datos y armando PDF de horas..."
    )

    datos, error = gamma_app.agente_excel.preparar_datos_reporte(descuento=descuento, incluir_iva=incluir_iva)
    if error:
        bot.send_message(message_obj.chat.id, error)
        return

    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)

    if ruta_pdf:
        with open(ruta_pdf, "rb") as f:
            bot.send_document(
                message_obj.chat.id,
                f,
                caption=f"📊 {msg_pdf}",
                visible_file_name=Path(ruta_pdf).name,
            )
    else:
        bot.send_message(message_obj.chat.id, msg_pdf)


def capturar_descuento_reporte(
    message: Message, bot: TeleBot, gamma_app: "GammaApp"
) -> None:
    """
    capturar_descuento_reporte method/function.

    Args:
        message: Description for message.
        bot: Description for bot.
        gamma_app: Description for gamma_app.

    Returns:
        Description of the return value.

    Raises:
        Exception: Description of the exception.
    """
    if not verificar_usuario_manual(bot, message):
        return
    if not message.text:
        bot.reply_to(
            message, "❌ Por favor, enviá un texto numérico. (No se admiten archivos)"
        )
        return

    try:
        chat_id = message.chat.id
        nombre_hoja = EstadoGestor.pop(f"reporte_{chat_id}")
        incluir_iva = EstadoGestor.pop(f"iva_{chat_id}", False)
        if not nombre_hoja:
            bot.reply_to(message, "❌ Sesión expirada. Ejecutá /reporte de nuevo.")
            return
        monto = float(message.text.strip().replace(".", "").replace(",", ""))
        generar_y_enviar_reporte_por_hoja(
            bot, gamma_app, message, nombre_hoja, descuento=monto, incluir_iva=incluir_iva
        )
    except ValueError:
        bot.reply_to(
            message,
            "❌ El monto debe ser numérico. Operación cancelada.\n"
            "Ejecutá /reporte para intentar de nuevo.",
        )


def generar_y_enviar_reporte_por_hoja(
    bot: TeleBot,
    gamma_app: "GammaApp",
    message_obj: Message,
    nombre_hoja: str,
    descuento: float,
    incluir_iva: bool = False,
) -> None:
    """
    generar_y_enviar_reporte_por_hoja method/function.

    Args:
        bot: Description for bot.
        gamma_app: Description for gamma_app.
        message_obj: Description for message_obj.
        nombre_hoja: Description for nombre_hoja.
        descuento: Description for descuento.
        incluir_iva: Si se debe incluir IVA en el reporte.

    Returns:
        Description of the return value.

    Raises:
        Exception: Description of the exception.
    """
    bot.send_message(
        message_obj.chat.id, "📄 Procesando datos y armando PDF de horas..."
    )

    datos, error = gamma_app.agente_excel.preparar_datos_reporte(
        nombre_hoja=nombre_hoja, descuento=descuento, incluir_iva=incluir_iva
    )
    if error:
        bot.send_message(message_obj.chat.id, error)
        return

    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)

    if ruta_pdf:
        with open(ruta_pdf, "rb") as f:
            bot.send_document(
                message_obj.chat.id,
                f,
                caption=f"📊 {msg_pdf}",
                visible_file_name=Path(ruta_pdf).name,
            )
    else:
        bot.send_message(message_obj.chat.id, msg_pdf)
