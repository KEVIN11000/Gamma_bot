from __future__ import annotations

import logging
import traceback
from functools import wraps
from typing import Any

from telebot import TeleBot


def safe_handler(bot: TeleBot, logger: logging.Logger) -> Any:
    """
    Decorador para capturar excepciones en handlers y evitar bloques try-except repetitivos.
    Envía un mensaje genérico al usuario si ocurre un error y lo registra en el logger.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            try:
                return func(obj, *args, **kwargs)
            except Exception as e:
                error_trace = traceback.format_exc()
                logger.error(
                    f"❌ Error interno en '{func.__name__}': {e}\n{error_trace}"
                )

                # Check if it's a RefreshError (invalid credentials)
                error_msg = "❌ Error interno en el bot. Inténtalo de nuevo más tarde."
                if "invalid_grant" in str(e) or e.__class__.__name__ == "RefreshError":
                    error_msg = "❌ Error de credenciales (Google Sheets). El administrador debe actualizar 'credentials.json' en el servidor y reiniciar la app."

                try:
                    if hasattr(obj, "data"):
                        # Es un CallbackQuery
                        bot.send_message(
                            obj.message.chat.id,
                            error_msg,
                        )
                        bot.answer_callback_query(obj.id, "Error interno.")
                    else:
                        # Es un Message
                        bot.reply_to(
                            obj,
                            error_msg,
                        )
                except Exception as send_e:
                    logger.error(
                        f"Error al enviar mensaje de error al usuario: {send_e}"
                    )

        return wrapper

    return decorator
