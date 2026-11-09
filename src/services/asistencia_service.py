from pathlib import Path
from typing import TYPE_CHECKING, Any
from telebot import TeleBot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

if TYPE_CHECKING:
    from com.bot import GAMMA as GammaApp
else:
    GammaApp = Any

from com.core.security import verificar_usuario_manual
from logger_config import setup_logger
from logic.logic import EstadoGestor
from logic.pdf_service import PDFService
from services.excel_service import ExcelReportService

logger = setup_logger("asistencia_service")


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
        generar_y_enviar_reporte(
            bot, gamma_app, message, descuento=monto_descuento, incluir_iva=incluir_iva
        )
    except ValueError:
        bot.reply_to(
            message,
            "❌ *Error:* El monto debe ser numérico.\n"
            "Operación de reporte abortada. Podés pedir el reporte de nuevo más tarde o cerrar otro ciclo.",
            parse_mode="Markdown",
        )


def generar_y_enviar_reporte(
    bot: TeleBot,
    gamma_app: "GammaApp",
    message_obj: Message,
    descuento: float,
    incluir_iva: bool = False,
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
        message_obj.chat.id, "📄 Procesando datos y armando reportes (PDF y Excel)..."
    )

    datos, error = gamma_app.agente_excel.preparar_datos_reporte(
        descuento=descuento, incluir_iva=incluir_iva
    )
    if error:
        bot.send_message(message_obj.chat.id, error)
        return

    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)
    excel_service = ExcelReportService()
    try:
        ruta_xlsx = excel_service.generar_reporte_horas(datos)
    except Exception:
        ruta_xlsx = None

    if ruta_pdf:
        with open(ruta_pdf, "rb") as f:
            bot.send_document(
                message_obj.chat.id,
                f,
                caption=f"📄 {msg_pdf}",
                visible_file_name=Path(ruta_pdf).name,
            )
    else:
        bot.send_message(message_obj.chat.id, msg_pdf)

    if ruta_xlsx:
        with open(ruta_xlsx, "rb") as f_x:
            bot.send_document(
                message_obj.chat.id,
                f_x,
                caption="📊 Planilla Excel (.xlsx) generada",
                visible_file_name=Path(ruta_xlsx).name,
            )


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
            bot,
            gamma_app,
            message,
            nombre_hoja,
            descuento=monto,
            incluir_iva=incluir_iva,
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
        message_obj.chat.id, "📄 Procesando datos y armando reportes (PDF y Excel)..."
    )

    datos, error = gamma_app.agente_excel.preparar_datos_reporte(
        nombre_hoja=nombre_hoja, descuento=descuento, incluir_iva=incluir_iva
    )
    if error:
        bot.send_message(message_obj.chat.id, error)
        return

    ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)
    excel_service = ExcelReportService()
    try:
        ruta_xlsx = excel_service.generar_reporte_horas(datos)
    except Exception:
        ruta_xlsx = None

    if ruta_pdf:
        with open(ruta_pdf, "rb") as f:
            bot.send_document(
                message_obj.chat.id,
                f,
                caption=f"📄 {msg_pdf}",
                visible_file_name=Path(ruta_pdf).name,
            )
    else:
        bot.send_message(message_obj.chat.id, msg_pdf)

    if ruta_xlsx:
        with open(ruta_xlsx, "rb") as f_x:
            bot.send_document(
                message_obj.chat.id,
                f_x,
                caption="📊 Planilla Excel (.xlsx) generada",
                visible_file_name=Path(ruta_xlsx).name,
            )


def procesar_comando_horas(
    bot: TeleBot,
    gamma_app: "GammaApp",
    message: Message,
) -> None:
    """Procesa el comando /horas para consultar métricas MTD y analíticas laborales."""
    bot.send_chat_action(message.chat.id, "typing")
    analiticas, error = (
        gamma_app.agente_excel.calcular_analiticas_asistencia()
        if hasattr(gamma_app, "agente_excel")
        else (None, "Módulo de horas no inicializado.")
    )

    if error or not analiticas:
        bot.reply_to(message, str(error or "Módulo de horas no disponible."))
        return

    periodo = analiticas["periodo"]
    horas_fmt = analiticas["total_horas_formato"]
    horas_dec = analiticas["total_horas_decimal"]
    dias = analiticas["dias_trabajados"]
    prom = analiticas["promedio_horas_por_dia"]
    salario = f"{analiticas['salario_acumulado_gs']:,}".replace(",", ".")
    tarifa = f"{analiticas['monto_por_hora']:,}".replace(",", ".")
    perdidas_fmt = analiticas["horas_perdidas_formato"]
    perdidas_dec = analiticas["horas_perdidas_decimal"]
    extras_fmt = analiticas["horas_extras_formato"]
    extras_dec = analiticas["horas_extras_decimal"]
    neto_fmt = analiticas["balance_neto_formato"]
    neto_dec = analiticas["balance_neto_decimal"]

    icono_balance = "✅" if neto_dec >= 0 else "⚠️"

    texto = (
        f"📊 *Analíticas de Asistencia MTD — {periodo}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 *Horas Trabajadas:* `{horas_fmt}` ({horas_dec:.2f}h)\n"
        f"📅 *Días Trabajados:* {dias} (Promedio: `{prom:.2f}h/día`)\n"
        f"💰 *Salario Acumulado:* `₲ {salario}` (Tarifa: `₲ {tarifa}/h`)\n\n"
        f"⏳ *Horas Perdidas (< 8h):* `{perdidas_fmt}` ({perdidas_dec:.2f}h)\n"
        f"🚀 *Horas Extras (> 8h):* `{extras_fmt}` ({extras_dec:.2f}h)\n"
        f"{icono_balance} *Balance Neto:* `{neto_fmt}` ({neto_dec:.2f}h)"
    )
    teclado = InlineKeyboardMarkup()
    teclado.row(
        InlineKeyboardButton("✏️ Modo Edición", callback_data="iniciar_modo_edicion")
    )
    bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=teclado)


def procesar_comando_periodo(
    bot: TeleBot,
    gamma_app: "GammaApp",
    message: Message,
) -> None:
    """Procesa el comando /periodo para consultar el estado de sincronización entre marcación y contabilidad."""
    bot.send_chat_action(message.chat.id, "typing")
    from logic.logic import obtener_estado_periodos

    repo = getattr(gamma_app, "repo", None)
    estado = obtener_estado_periodos(repo=repo)

    periodo_lab = estado["periodo_laboral"]
    periodo_cont = estado["periodo_contable"]
    sinc = estado["sincronizados"]

    estado_str = "✅ *Sincronizados*" if sinc else "⚠️ *Desincronizados*"
    aviso_sinc = (
        ""
        if sinc
        else (
            "\n\n💡 *Aviso:* Los períodos no coinciden. Ejecutá el cierre"
            " correspondiente para alinearlos."
        )
    )

    texto = (
        "🗓️ *Estado de Períodos Activos*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 *Período Laboral:* `{periodo_lab}`\n"
        f"📚 *Período Contable:* `{periodo_cont}`\n"
        f"🔄 *Estado:* {estado_str}"
        f"{aviso_sinc}"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")


def limpiar_salida_jornada(
    fecha: str,
    repo: Any | None = None,
    sync_sheets: bool = True,
) -> dict[str, Any]:
    """Elimina la marca de salida de una fecha determinada reabriendo la jornada."""
    from datetime import datetime
    import os
    from repositories.local_repository import get_local_repository

    if repo is None:
        repo = get_local_repository()

    try:
        dt = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return {"exito": False, "mensaje": f"Formato de fecha inválido: '{fecha}'."}

    jornada = repo.obtener_jornada_por_fecha(fecha)
    if not jornada:
        return {"exito": False, "mensaje": f"No existe registro para la fecha {fecha}."}

    if not jornada.get("hora_salida"):
        return {
            "exito": False,
            "mensaje": f"No hay salida registrada para la fecha {fecha}.",
        }

    salida_anterior = jornada.get("hora_salida")
    repo.actualizar_jornada(
        fecha,
        hora_salida=None,
        horas_decimal=0.0,
        auto_cerrado=0,
        sincronizado_sheets=0,
    )
    jornada_actualizada = repo.obtener_jornada_por_fecha(fecha) or {}

    sinc_ok = False
    if sync_sheets:
        try:
            from services.sync_service import SyncService

            s_id = os.getenv("SPREADSHEET_ID")
            if s_id:
                sync_svc = SyncService(local_repo=repo, spreadsheet_id=s_id)
                res_sync = sync_svc.volcar_local_a_sheets(
                    mes=dt.month, anio=dt.year, modulo="laboral", forzar=True
                )
                sinc_ok = bool(res_sync.get("exito", False))
        except Exception as e_sync:
            logger.warning(f"Error sincronizando limpieza de salida a Sheets: {e_sync}")

    return {
        "exito": True,
        "mensaje": (
            f"Salida ({salida_anterior}) eliminada correctamente. La jornada quedó abierta."
        ),
        "jornada": jornada_actualizada,
        "sincronizado_sheets": sinc_ok,
    }


def rectificar_jornada_asistencia(
    fecha: str,
    hora_entrada: str | None = None,
    hora_salida_almuerzo: str | None = None,
    hora_vuelta_almuerzo: str | None = None,
    hora_salida: str | None = None,
    modo: str = "normal",
    sync_sheets: bool = True,
    repo: Any | None = None,
) -> dict[str, Any]:
    """Rectifica los horarios de una jornada puntual y reconcilia con Google Sheets."""
    from datetime import datetime
    import os
    from logic.logic import DIAS_SEMANA, AgenteAutonomoHoras
    from repositories.local_repository import get_local_repository

    if repo is None:
        repo = get_local_repository()

    try:
        dt = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return {"exito": False, "mensaje": f"Formato de fecha inválido: '{fecha}'."}

    nombre_dia = DIAS_SEMANA[dt.weekday()]
    repo.obtener_o_crear_jornada(fecha=fecha, dia=nombre_dia, modo=modo)

    horas_dec = AgenteAutonomoHoras.calcular_horas_jornada(
        hora_entrada,
        hora_salida_almuerzo,
        hora_vuelta_almuerzo,
        hora_salida,
    )

    campos: dict[str, Any] = {
        "hora_entrada": hora_entrada,
        "hora_salida_almuerzo": hora_salida_almuerzo,
        "hora_vuelta_almuerzo": hora_vuelta_almuerzo,
        "hora_salida": hora_salida,
        "horas_decimal": horas_dec,
        "modo": modo,
        "sincronizado_sheets": 0,
    }
    repo.actualizar_jornada(fecha, **campos)
    jornada_actualizada = repo.obtener_jornada_por_fecha(fecha) or {}

    sinc_ok = False
    if sync_sheets:
        try:
            from services.sync_service import SyncService

            s_id = os.getenv("SPREADSHEET_ID")
            if s_id:
                sync_svc = SyncService(local_repo=repo, spreadsheet_id=s_id)
                res_sync = sync_svc.volcar_local_a_sheets(
                    mes=dt.month, anio=dt.year, modulo="laboral", forzar=True
                )
                sinc_ok = bool(res_sync.get("exito", False))
        except Exception as e_sync:
            logger.warning(f"Error sincronizando rectificación a Sheets: {e_sync}")

    return {
        "exito": True,
        "mensaje": f"Jornada del {fecha} actualizada exitosamente.",
        "horas_decimal": horas_dec,
        "jornada": jornada_actualizada,
        "sincronizado_sheets": sinc_ok,
    }


def iniciar_flujo_edicion_asistencia(bot: TeleBot, chat_id: int) -> None:
    """Inicia el desafío de seguridad solicitando X-API-KEY para habilitar el modo edición."""
    msg = bot.send_message(
        chat_id,
        "🔒 <b>Modo Edición de Asistencia</b>\n\n"
        "Ingresa tu <code>X-API-KEY</code> para autenticarte.\n"
        "<i>(Tu mensaje con la clave será eliminado de inmediato por seguridad).</i>",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _step_verificar_clave_edicion, bot)


def _step_verificar_clave_edicion(message: Message, bot: TeleBot) -> None:
    """Verifica la API key y elimina el mensaje con la clave inmediatamente."""
    chat_id = message.chat.id
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    from api.security import is_valid_api_key

    clave = (message.text or "").strip()
    if not is_valid_api_key(clave):
        bot.send_message(
            chat_id,
            "❌ <b>Acceso denegado:</b> Clave incorrecta.",
            parse_mode="HTML",
        )
        return

    teclado = InlineKeyboardMarkup()
    teclado.row(
        InlineKeyboardButton(
            "🔄 Limpiar salida de hoy", callback_data="edit_asist:limpiar_hoy"
        )
    )
    teclado.row(
        InlineKeyboardButton(
            "📅 Rectificar ayer", callback_data="edit_asist:rectificar_ayer"
        )
    )
    teclado.row(
        InlineKeyboardButton(
            "✏️ Rectificar por fecha", callback_data="edit_asist:rectificar_fecha"
        )
    )
    teclado.row(
        InlineKeyboardButton("❌ Cancelar", callback_data="edit_asist:cancelar")
    )

    bot.send_message(
        chat_id,
        "🔓 <b>Modo Edición Habilitado</b>\n\nSelecciona la acción a realizar:",
        reply_markup=teclado,
        parse_mode="HTML",
    )


def procesar_callback_edicion_asistencia(call: Any, bot: TeleBot) -> None:
    """Maneja los callbacks interactivos del modo edición."""
    from datetime import timedelta
    from logic.logic import get_now_py

    accion = call.data.split(":", 1)[1] if ":" in call.data else ""
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if accion == "cancelar":
        bot.edit_message_text("❌ Sesión de edición finalizada.", chat_id, msg_id)
        return

    ahora = get_now_py()
    hoy_iso = ahora.strftime("%Y-%m-%d")

    if accion == "limpiar_hoy":
        bot.edit_message_text("⏳ Limpiando salida de hoy...", chat_id, msg_id)
        res = limpiar_salida_jornada(hoy_iso, sync_sheets=True)
        if res.get("exito"):
            bot.edit_message_text(
                f"✅ <b>{res['mensaje']}</b>\n\n"
                "La celda de salida en Google Sheets fue limpiada y la jornada quedó abierta. "
                "Ya puedes marcar normalmente al retirarte.",
                chat_id,
                msg_id,
                parse_mode="HTML",
            )
        else:
            bot.edit_message_text(
                f"⚠️ {res.get('mensaje', 'No se pudo limpiar la salida.')}",
                chat_id,
                msg_id,
            )
        return

    if accion == "rectificar_ayer":
        ayer_iso = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
        _pedir_horarios_rectificacion(bot, chat_id, ayer_iso)
        return

    if accion == "rectificar_fecha":
        msg = bot.send_message(
            chat_id,
            "📅 <b>Ingresa la fecha a rectificar:</b>\n"
            "Formato: <code>YYYY-MM-DD</code> (ej. <i>2026-11-04</i>)",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _step_capturar_fecha_rectificar, bot)
        return


def _pedir_horarios_rectificacion(bot: TeleBot, chat_id: int, fecha: str) -> None:
    """Pide los horarios para una fecha determinada."""
    msg = bot.send_message(
        chat_id,
        f"📅 <b>Rectificando jornada {fecha}</b>\n\n"
        "Envía los horarios separados por coma o espacio:\n"
        "<code>ENTRADA, SALIDA_ALMUERZO, VUELTA_ALMUERZO, SALIDA</code>\n\n"
        "<i>Ejemplo con almuerzo:</i> <code>08:45, 12:00, 13:00, 17:06</code>\n"
        "<i>Ejemplo sin almuerzo:</i> <code>08:45, -, -, 17:06</code>",
        parse_mode="HTML",
    )
    bot.register_next_step_handler(msg, _step_capturar_horarios_rectificar, bot, fecha)


def _step_capturar_fecha_rectificar(message: Message, bot: TeleBot) -> None:
    """Valida la fecha ingresada y solicita los horarios."""
    from datetime import datetime

    fecha_txt = (message.text or "").strip()
    try:
        datetime.strptime(fecha_txt, "%Y-%m-%d")
    except ValueError:
        bot.send_message(
            message.chat.id,
            f"❌ Formato de fecha inválido: '<code>{fecha_txt}</code>'. Debe ser <code>YYYY-MM-DD</code>.",
            parse_mode="HTML",
        )
        return

    _pedir_horarios_rectificacion(bot, message.chat.id, fecha_txt)


def _step_capturar_horarios_rectificar(
    message: Message, bot: TeleBot, fecha: str
) -> None:
    """Parsea y valida los 4 tramos y aplica la rectificación."""
    import re

    texto = (message.text or "").strip()
    if texto.lower() in ("cancelar", "salir", "/cancelar"):
        bot.send_message(message.chat.id, "❌ Operación cancelada.")
        return

    # Separar por comas o espacios
    if "," in texto:
        partes = [p.strip() for p in texto.split(",")]
    else:
        partes = texto.split()

    if len(partes) != 4:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Debes ingresar exactamente 4 tramos:</b>\n"
            "<code>ENTRADA, S.ALMUERZO, V.ALMUERZO, SALIDA</code>\n"
            "Usa guion <code>-</code> para los tramos vacíos.",
            parse_mode="HTML",
        )
        return

    def _limpiar_tramo(t: str) -> str | None:
        t_clean = t.strip()
        if t_clean in ("-", "--", "none", "null", "", "0"):
            return None
        return t_clean

    entrada = _limpiar_tramo(partes[0])
    sal_alm = _limpiar_tramo(partes[1])
    vta_alm = _limpiar_tramo(partes[2])
    salida = _limpiar_tramo(partes[3])

    patron = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    for nombre, val in [
        ("Entrada", entrada),
        ("S. Almuerzo", sal_alm),
        ("V. Almuerzo", vta_alm),
        ("Salida", salida),
    ]:
        if val and not re.match(patron, val):
            bot.send_message(
                message.chat.id,
                f"❌ Formato de hora inválido en <b>{nombre}</b>: '<code>{val}</code>'. Debe ser HH:MM (00:00 - 23:59).",
                parse_mode="HTML",
            )
            return

    if entrada and salida and salida < entrada:
        bot.send_message(
            message.chat.id,
            "❌ La hora de salida no puede ser anterior a la hora de entrada.",
        )
        return

    modo = "directo" if (sal_alm is None and vta_alm is None) else "normal"
    msg_espera = bot.send_message(
        message.chat.id, "⏳ Guardando rectificación y sincronizando a Sheets..."
    )

    res = rectificar_jornada_asistencia(
        fecha=fecha,
        hora_entrada=entrada,
        hora_salida_almuerzo=sal_alm,
        hora_vuelta_almuerzo=vta_alm,
        hora_salida=salida,
        modo=modo,
        sync_sheets=True,
    )

    if res.get("exito"):
        h_dec = res.get("horas_decimal", 0.0)
        sinc_txt = (
            "✅ Reconciliado en Google Sheets"
            if res.get("sincronizado_sheets")
            else "⚠️ Pendiente de sync a Sheets"
        )
        bot.edit_message_text(
            f"✅ <b>Jornada del {fecha} rectificada con éxito</b>\n\n"
            f"🕒 <b>Entrada:</b> {entrada or '-'}\n"
            f"☕ <b>Almuerzo:</b> {sal_alm or '-'} a {vta_alm or '-'}\n"
            f"🚪 <b>Salida:</b> {salida or '-'}\n"
            f"⏱️ <b>Horas Computadas:</b> {h_dec:.2f}h\n"
            f"🔄 <b>Estado Sheets:</b> {sinc_txt}",
            message.chat.id,
            msg_espera.message_id,
            parse_mode="HTML",
        )
    else:
        bot.edit_message_text(
            f"❌ Error al rectificar: {res.get('mensaje', 'Error desconocido')}",
            message.chat.id,
            msg_espera.message_id,
        )
