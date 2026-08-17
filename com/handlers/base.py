from __future__ import annotations
import os
from typing import Any
from pathlib import Path
from telebot import TeleBot
from telebot.types import BotCommand
from logger_config import setup_logger
from com.core.security import auth_required
from com.core.errors import safe_handler

logger = setup_logger("base_handler")

def _registrar_comandos_menu(bot: TeleBot) -> Any:
    comandos = [
        BotCommand("gasto",    "Registrar un nuevo gasto (ej. '/gasto 15000 taxi')."),
        BotCommand("ingreso",  "Registrar un nuevo ingreso."),
        BotCommand("balance",  "Ver el balance financiero mensual."),
        BotCommand("marcar",   "Registrar entrada/salida general."),
        BotCommand("marcar_materia", "Registrar asistencia a materias."),
        BotCommand("reporte",  "Generar reporte PDF de un período anterior."),
        BotCommand("aviso",    "Agendar un hito o recordatorio con IA."),
        BotCommand("avisos",   "Ver lista de avisos activos."),
        BotCommand("cierre",   "Ejecutar cierre de período de marcaciones."),
        BotCommand("start",    "Actualizar menú de comandos")
    ]
    
    if os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true":
        comandos.append(BotCommand("debug", "Ver logs recientes del sistema."))
        
    bot.set_my_commands(comandos)
logger.info("✅ Menú de comandos actualizado.")

def register_base_handlers(bot: TeleBot, gamma_app: Any) -> Any:
    @bot.message_handler(commands=['debug'])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_debug(message):
        modo_dev = os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true"
        if not modo_dev:
            bot.reply_to(message, "🔒 El comando de depuración está desactivado en este entorno de producción.")
            return
            
        partes = message.text.split(" ", 1)
        tipo_log = partes[1].strip().lower() if len(partes) > 1 else "app"
        
        archivos = {
            "app": "gen_log.txt",
            "error": "/var/log/kevin11000.pythonanywhere.com.error.log",
            "server": "/var/log/kevin11000.pythonanywhere.com.server.log",
            "access": "/var/log/kevin11000.pythonanywhere.com.access.log"
        }
        
        if tipo_log not in archivos:
            msg = "⚠️ *Comando incorrecto.*\nUsa:\n`/debug app` (logs internos)\n`/debug error` (logs de PA)\n`/debug server` (logs server)\n`/debug access` (logs web)"
            bot.reply_to(message, msg, parse_mode="Markdown")
            return
            
        ruta_archivo = archivos[tipo_log]
        
        if Path(ruta_archivo).exists():
            with open(ruta_archivo, "r", encoding="utf-8", errors="replace") as f:
                lineas = f.readlines()
                ultimas = "".join(lineas[-20:])
            if not ultimas.strip():
                ultimas = "[El archivo existe pero está vacío]"
            bot.reply_to(message, f"🛠️ *ÚLTIMOS LOGS ({tipo_log.upper()}):*\n```text\n{ultimas[-3000:]}\n```", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"📭 El archivo `{ruta_archivo}` no existe.\n_(Normal si estás corriendo el bot en Windows localmente)_", parse_mode="Markdown")

    @bot.message_handler(commands=['start'])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def comando_start(message):
        _registrar_comandos_menu(bot)
        
        modo_dev = os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true"
        texto_debug = "🛠️ /debug   — Ver logs de errores internos\n" if modo_dev else ""
        
        # Leer archivo VERSION
        version = "1.x"
        base_path = Path(__file__).resolve().parents[3]
        version_path = base_path / "VERSION"
        if version_path.exists():
            with open(version_path, "r") as f:
                version = f.read().strip()
                
        texto = (
            f"🤖 *Bot de Gestión Avanzada (GAMMA)* `{version}`\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Menú de comandos sincronizado ✅\n\n"
            "*Finanzas:*\n"
            "💸 /gasto — Registrar gasto por texto\n"
            "💰 /ingreso — Registrar ingreso\n"
            "📊 /balance — Ver tu balance\n"
            "📷 Envia una foto de factura para leerla (OCR)\n\n"
            "*Asistencia:*\n"
            "▶️ /marcar  — Registrar entrada o salida\n"
            "📚 /marcar\\_materia — Asistencia a materias\n"
            "📄 /reporte — Generar PDF\n\n"
            "*Avisos:*\n"
            "✍️ /aviso   — Agendar recordatorios\n"
            "📋 /avisos  — Gestionar recordatorios\n"
            f"{texto_debug}"
        )
        bot.reply_to(message, texto, parse_mode="Markdown")
