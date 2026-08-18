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

                try:
                    if hasattr(obj, "data"):
                        # Es un CallbackQuery
                        bot.send_message(
                            obj.message.chat.id,
                            "❌ Error interno en el bot. Inténtalo de nuevo más tarde.",
                        )
                        bot.answer_callback_query(obj.id, "Error interno.")
                    else:
                        # Es un Message
                        bot.reply_to(
                            obj,
                            "❌ Error interno en el bot. Inténtalo de nuevo más tarde.",
                        )
                except Exception as send_e:
                    logger.error(
                        f"Error al enviar mensaje de error al usuario: {send_e}"
                    )

        return wrapper

    return decorator
