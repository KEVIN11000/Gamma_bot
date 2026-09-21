"""Handler de Soporte y Reporte de Tickets para Telegram.

Permite al usuario levantar reportes de bugs, sugerencias de cambio o consultas
técnicas desde su teléfono hacia la bandeja de incidentes Vigía.
Cumple con el patrón Modo Dual (OCP): ejecución directa con argumentos o
asistente guiado interactivo por botones sin argumentos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from telebot import TeleBot
from telebot.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from com.core.errors import safe_handler
from com.core.security import auth_required
from com.core.states import clear_state, get_state, set_state
from com.core.telemetry import reportar_incidente_vigia
from logger_config import setup_logger

logger = setup_logger("soporte_handler")
BASE_DIR = Path(__file__).resolve().parents[2]
FALLBACK_TICKETS_FILE = BASE_DIR / "incidentes_telegram.json"


def _guardar_ticket_fallback(ticket_data: Dict[str, Any]) -> None:
    """Guarda una copia del ticket en disco en caso de que GitHub API no esté disponible."""
    try:
        tickets = []
        if FALLBACK_TICKETS_FILE.exists():
            try:
                with open(FALLBACK_TICKETS_FILE, "r", encoding="utf-8") as f:
                    tickets = json.load(f)
            except Exception:
                tickets = []
        tickets.append(ticket_data)
        with open(FALLBACK_TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(tickets, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando ticket en fallback local: {e}")


def _procesar_y_confirmar_soporte(
    bot: TeleBot,
    chat_id: int,
    tipo: str,
    descripcion: str,
    autor: str,
) -> None:
    """Registra el ticket de soporte y envía confirmación limpia al usuario."""
    clean_desc = descripcion.strip()
    titulo_resumido = clean_desc[:70] + ("..." if len(clean_desc) > 70 else "")
    titulo = f"[{tipo.upper()}] {titulo_resumido}"
    detalle = f"Reportado por @{autor} vía Telegram:\n\n{clean_desc}"

    # 1. Intentar registrar en GitHub Issues vía telemetría
    enviado = reportar_incidente_vigia(
        titulo=titulo,
        detalle=detalle,
        origen="telegram-soporte",
    )

    # 2. Guardar siempre en fallback local por resiliencia
    import datetime

    ahora_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _guardar_ticket_fallback(
        {
            "tipo": tipo,
            "titulo": titulo,
            "descripcion": clean_desc,
            "autor": autor,
            "fecha": ahora_iso,
            "enviado_github": enviado,
        }
    )

    logger.info(
        f"Ticket de soporte registrado: '{titulo}' por @{autor} (GH: {enviado})"
    )

    iconos = {
        "bug": "🐛",
        "sugerencia": "💡",
        "soporte": "❓",
    }
    icono = iconos.get(tipo.lower(), "📝")

    bot.send_message(
        chat_id,
        f"✅ <b>¡Ticket registrado con éxito!</b>\n\n"
        f"{icono} <b>Tipo:</b> {tipo.capitalize()}\n"
        f"📄 <b>Detalle:</b> {clean_desc}\n\n"
        f"<i>Tu reporte ha sido depositado en la bandeja de incidentes. "
        f"Será revisado en la próxima sesión de mantenimiento local.</i>",
        parse_mode="HTML",
    )


def _inferir_tipo_y_descripcion(texto_inline: str) -> tuple[str, str]:
    """Infiere el tipo de ticket a partir del texto con argumentos inline."""
    palabras = texto_inline.split(maxsplit=1)
    if not palabras:
        return "soporte", ""

    primera = palabras[0].lower()
    resto = palabras[1] if len(palabras) > 1 else ""

    if primera in ("bug", "error", "fallo"):
        return "bug", resto if resto else primera
    elif primera in ("sugerencia", "idea", "mejora"):
        return "sugerencia", resto if resto else primera
    elif primera in ("consulta", "soporte", "ayuda"):
        return "soporte", resto if resto else primera
    else:
        return "soporte", texto_inline


def register_soporte_handlers(bot: TeleBot, gamma_app: Any) -> None:
    """Registra los manejadores de comando /soporte y su flujo interactivo."""

    @bot.message_handler(commands=["soporte"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_soporte(message: Message) -> None:
        texto = message.text or ""
        # Quitar el comando '/soporte'
        partes = texto.split(maxsplit=1)
        args_inline = partes[1].strip() if len(partes) > 1 else ""

        user_id = message.from_user.id if message.from_user else message.chat.id
        autor = (
            message.from_user.username or message.from_user.first_name
            if message.from_user
            else "Usuario"
        )

        # MODO DIRECTO (si vienen argumentos inline)
        if args_inline:
            clear_state(user_id)
            tipo, desc = _inferir_tipo_y_descripcion(args_inline)
            _procesar_y_confirmar_soporte(bot, message.chat.id, tipo, desc, autor)
            return

        # MODO INTERACTIVO (sin argumentos)
        clear_state(user_id)
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(
                "🐛 Reportar Bug / Error", callback_data="soporte_tipo:bug"
            ),
            InlineKeyboardButton(
                "💡 Sugerencia de Cambio",
                callback_data="soporte_tipo:sugerencia",
            ),
            InlineKeyboardButton(
                "❓ Consulta / Soporte General",
                callback_data="soporte_tipo:soporte",
            ),
            InlineKeyboardButton("❌ Cancelar", callback_data="soporte_cancelar"),
        )

        bot.send_message(
            message.chat.id,
            "🛠️ <b>Centro de Soporte e Incidentes</b>\n\n"
            "Selecciona el tipo de ticket que deseas levantar:",
            parse_mode="HTML",
            reply_markup=markup,
        )

    @bot.callback_query_handler(
        func=lambda call: call.data and call.data.startswith("soporte_")
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_soporte_callback(call: CallbackQuery) -> None:
        user_id = call.from_user.id if call.from_user else call.message.chat.id
        data = call.data or ""

        if data == "soporte_cancelar":
            clear_state(user_id)
            bot.answer_callback_query(call.id, "Cancelado")
            bot.edit_message_text(
                "❌ Operación de soporte cancelada.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
            return

        tipo = data.split(":", 1)[1] if ":" in data else "soporte"
        set_state(user_id, "SOPORTE_ESPERANDO_TEXTO", {"tipo": tipo})
        bot.answer_callback_query(call.id)

        iconos = {
            "bug": "🐛 Bug",
            "sugerencia": "💡 Sugerencia",
            "soporte": "❓ Consulta",
        }
        label = iconos.get(tipo, "📝 Soporte")

        bot.edit_message_text(
            f"Seleccionaste: <b>{label}</b>\n\n"
            f"✍️ <i>Escribe a continuación el detalle de tu mensaje o problema:</i>\n\n"
            f"💡 <i>Puedes enviar /cancelar en cualquier momento para abortar.</i>",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
        )

    @bot.message_handler(
        func=lambda msg: not msg.text.startswith("/")
        and (get_state(msg.from_user.id if msg.from_user else msg.chat.id) or {}).get(
            "estado"
        )
        == "SOPORTE_ESPERANDO_TEXTO"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_soporte_texto(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else message.chat.id
        state_dict = get_state(user_id) or {}
        datos = state_dict.get("datos", {})
        tipo = datos.get("tipo", "soporte")
        clear_state(user_id)

        autor = (
            message.from_user.username or message.from_user.first_name
            if message.from_user
            else "Usuario"
        )
        _procesar_y_confirmar_soporte(
            bot, message.chat.id, tipo, message.text or "", autor
        )
