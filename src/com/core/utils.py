import json
import os
import threading
import time
from typing import Any

PENDING_FILE = os.path.join("data", "pending_deletions.json")

def _load_pending() -> dict:
    if not os.path.exists(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_pending(data: dict):
    os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
    with open(PENDING_FILE, "w") as f:
        json.dump(data, f)

def limpiar_menus_expirados(bot: Any):
    data = _load_pending()
    now = time.time()
    to_delete = []
    for msg_key, expire_time in data.items():
        if now > expire_time:
            to_delete.append(msg_key)
    
    for msg_key in to_delete:
        try:
            chat_id, message_id = msg_key.split("_")
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        del data[msg_key]
        
    if to_delete:
        _save_pending(data)

def reply_with_expiration(bot: Any, chat_id: Any, text: str, timeout: int = 30, **kwargs):
    msg = bot.send_message(chat_id, text, **kwargs)
    
    # Save to file queue
    data = _load_pending()
    msg_key = f"{msg.chat.id}_{msg.message_id}"
    data[msg_key] = time.time() + timeout
    _save_pending(data)
    
    # Try with thread
    def delete_task():
        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except Exception:
            pass
        d = _load_pending()
        if msg_key in d:
            del d[msg_key]
            _save_pending(d)
            
    threading.Timer(timeout, delete_task).start()
    return msg
