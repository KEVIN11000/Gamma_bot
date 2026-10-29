import json  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
from typing import Any, Dict, Optional, Union  # noqa: E402

_UTILS_BASE = _Path(__file__).resolve().parents[2]  # resolves to src/
PENDING_FILE = str(_UTILS_BASE / "data" / "pending_deletions.json")
_PENDING_LOCK = threading.Lock()

logger = logging.getLogger("utils")


def _load_pending() -> dict:
    with _PENDING_LOCK:
        if not os.path.exists(PENDING_FILE):
            return {}
        try:
            with open(PENDING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando archivo pending_deletions: {e}")
            return {}


def _save_pending(data: dict) -> None:
    with _PENDING_LOCK:
        try:
            os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
            with open(PENDING_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error guardando pending_deletions: {e}")


def eliminar_mensaje_seguro(bot: Any, chat_id: Any, message_id: Any) -> bool:
    """Intenta eliminar un mensaje en Telegram capturando silenciosamente excepciones."""
    if not bot or not chat_id or not message_id or message_id == -1:
        return False
    try:
        bot.delete_message(chat_id, message_id)
        return True
    except Exception as e:
        err_msg = str(e).lower()
        if (
            "message to delete not found" in err_msg
            or "message can't be deleted" in err_msg
            or "chat not found" in err_msg
        ):
            logger.debug(
                f"Mensaje {message_id} en chat {chat_id} ya eliminado o no modificable: {e}"
            )
            return True
        logger.warning(
            f"No se pudo eliminar mensaje {message_id} en chat {chat_id}: {e}"
        )
        return False


def remover_teclado_inline(bot: Any, chat_id: Any, message_id: Any) -> bool:
    """Neutraliza el markup de una botonera interactiva sin borrar el texto del mensaje."""
    if not bot or not chat_id or not message_id or message_id == -1:
        return False
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        return True
    except Exception as e:
        err_msg = str(e).lower()
        if (
            "message is not modified" in err_msg
            or "message to edit not found" in err_msg
            or "chat not found" in err_msg
        ):
            logger.debug(
                f"Teclado de mensaje {message_id} en chat {chat_id} ya removido: {e}"
            )
            return True
        logger.warning(
            f"No se pudo remover teclado de mensaje {message_id} en chat {chat_id}: {e}"
        )
        return False


def limpiar_menus_expirados(bot: Any) -> int:
    """Recorre y procesa las acciones expiradas en pending_deletions de forma resiliente."""
    data = _load_pending()
    if not data:
        return 0

    now = time.time()
    to_purge = []
    processed_count = 0

    for msg_key, item in list(data.items()):
        expire_time = (
            item
            if isinstance(item, (int, float))
            else item.get("expire_at", 0) if isinstance(item, dict) else 0
        )
        action = (
            "delete" if not isinstance(item, dict) else item.get("action", "delete")
        )

        if now > expire_time:
            to_purge.append(msg_key)
            try:
                parts = str(msg_key).split("_")
                if len(parts) >= 2:
                    chat_id, message_id = parts[0], parts[1]
                    if action == "clear_markup":
                        remover_teclado_inline(bot, chat_id, message_id)
                    else:
                        eliminar_mensaje_seguro(bot, chat_id, message_id)
                    processed_count += 1
            except Exception as e:
                logger.debug(f"Error procesando expiración de {msg_key}: {e}")

    for msg_key in to_purge:
        data.pop(msg_key, None)

    if to_purge:
        _save_pending(data)

    return processed_count


class MockChat:
    def __init__(self, chat_id):
        self.id = chat_id


class MockMessage:
    def __init__(self, chat_id, message_id):
        self.chat = MockChat(chat_id)
        self.message_id = message_id


def reply_with_expiration(
    bot: Any, chat_id: Any, text: str, timeout: int = 30, **kwargs
):
    try:
        msg = bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.error(f"Error sending message to {chat_id}: {e}")
        # Return a mock message so the caller doesn't break
        return MockMessage(chat_id, -1)

    # Save to file queue
    data = _load_pending()
    msg_key = f"{msg.chat.id}_{msg.message_id}"
    data[msg_key] = time.time() + timeout
    _save_pending(data)

    # Try with thread
    def delete_task():
        eliminar_mensaje_seguro(bot, msg.chat.id, msg.message_id)
        d = _load_pending()
        if msg_key in d:
            del d[msg_key]
            _save_pending(d)

    threading.Timer(timeout, delete_task).start()
    return msg
