import os
import re
from functools import wraps
from telebot import TeleBot
from logger_config import setup_logger

logger = setup_logger("security")

def get_authorized_users() -> set:
    chat_id_raw = os.getenv("CHAT_ID", "")
    usuarios = set()
    pattern = r"^-?\d+$"
    for uid in chat_id_raw.split(','):
        uid = uid.strip()
        if re.match(pattern, uid):
            usuarios.add(int(uid))
    return usuarios

def auth_required(bot: TeleBot):
    """
    Decorador para restringir el acceso solo a usuarios autorizados.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(obj, *args, **kwargs):
            usuarios_permitidos = get_authorized_users()
            if obj.from_user.id not in usuarios_permitidos:
                if hasattr(obj, 'data'):
                    bot.answer_callback_query(obj.id, "No estás autorizado.", show_alert=True)
                else:
                    user = obj.from_user
                    alerta = (
                        f"🚫 Acceso no autorizado\n"
                        f"ID: {user.id} | @{user.username or 'sin username'}\n"
                        f"Nombre: {user.first_name} {user.last_name or ''}"
                    )
                    logger.info(alerta)
                    bot.reply_to(obj, "🚫 No tenés acceso a este bot.")
                return
            return func(obj, *args, **kwargs)
        return wrapper
    return decorator

def verificar_usuario_manual(bot: TeleBot, obj) -> bool:
    """
    Utilidad para verificar manualmente (ej. en next_step_handlers) 
    y enviar el mensaje de rechazo si no está autorizado.
    """
    usuarios_permitidos = get_authorized_users()
    if obj.from_user.id not in usuarios_permitidos:
        user = obj.from_user
        alerta = (
            f"🚫 Acceso no autorizado (Step Handler)\n"
            f"ID: {user.id} | @{user.username or 'sin username'}\n"
            f"Nombre: {user.first_name} {user.last_name or ''}"
        )
        logger.info(alerta)
        bot.reply_to(obj, "🚫 No tenés acceso a este bot.")
        return False
    return True
