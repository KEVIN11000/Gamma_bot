from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, Optional, Union

from adapters.notifications.telegram_adapter import TelegramNotificationAdapter
from adapters.notifications.whatsapp_adapter import WhatsAppNotificationAdapter
from logger_config import setup_logger
from ports.notification_port import INotificationPort
from services.notification_dispatcher import NotificationDispatcher

logger = setup_logger("worker")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "cola.db"


def _resolve_notifier(bot_or_notifier: Any) -> INotificationPort:
    """Wraps a legacy bot object in TelegramNotificationAdapter if needed."""
    if isinstance(bot_or_notifier, INotificationPort):
        return bot_or_notifier
    return TelegramNotificationAdapter(bot=bot_or_notifier)


def create_default_dispatcher(bot: Any = None) -> NotificationDispatcher:
    """Builds a configured NotificationDispatcher with auto-detected channel adapters."""
    import os

    dispatcher = NotificationDispatcher(default_channel="telegram")
    if bot is not None:
        dispatcher.register_adapter("telegram", _resolve_notifier(bot))

    wa_api_url = os.getenv("WHATSAPP_API_URL")
    if wa_api_url:
        try:
            wa_adapter = WhatsAppNotificationAdapter()
            dispatcher.register_adapter("whatsapp", wa_adapter)
            logger.info("Auto-registered WhatsAppNotificationAdapter in dispatcher")
        except Exception as exc:
            logger.warning(f"Could not auto-register WhatsApp adapter: {exc}")

    try:
        from adapters.notifications.push_adapter import PushNotificationAdapter

        push_adapter = PushNotificationAdapter()
        dispatcher.register_adapter("push", push_adapter)
        logger.info("Auto-registered PushNotificationAdapter in dispatcher")
    except Exception as exc:
        logger.warning(f"Could not auto-register Push adapter: {exc}")

    return dispatcher


def get_connection(
    db_path: Optional[Union[Path, str]] = None,
) -> sqlite3.Connection:
    """Returns a connection to the SQLite database with timeout=15.0 and WAL mode."""
    target_path = str(db_path or DB_PATH)
    conn = sqlite3.connect(target_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
    except Exception:
        pass
    return conn


def init_db(db_path: Optional[Union[Path, str]] = None) -> None:
    """Initializes the database schema for the queue with non-destructive migrations."""
    try:
        conn = get_connection(db_path)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recipient_id TEXT,
                        channel TEXT NOT NULL DEFAULT 'telegram',
                        chat_id INTEGER,
                        operacion TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        estado TEXT NOT NULL DEFAULT 'pendiente',
                        reintentos INTEGER NOT NULL DEFAULT 0,
                        next_retry INTEGER NOT NULL DEFAULT 0,
                        creado_at INTEGER NOT NULL
                    )
                    """)

                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(queue);")
                existing_cols = {row["name"] for row in cursor.fetchall()}

                if "recipient_id" not in existing_cols:
                    conn.execute("ALTER TABLE queue ADD COLUMN recipient_id TEXT;")
                    conn.execute(
                        "UPDATE queue SET recipient_id = CAST(chat_id AS TEXT) "
                        "WHERE recipient_id IS NULL AND chat_id IS NOT NULL;"
                    )
                    logger.info("Migrated queue schema: added recipient_id column")

                if "channel" not in existing_cols:
                    conn.execute(
                        "ALTER TABLE queue ADD COLUMN channel TEXT NOT NULL DEFAULT 'telegram';"
                    )
                    logger.info("Migrated queue schema: added channel column")

                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_queue_estado_retry ON queue (estado, next_retry, creado_at);"
                )
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")


# Initialize DB on module import
init_db()


def despachar_trabajo(
    bot_or_notifier: Any,
    operacion: str,
    payload: Dict[str, Any],
    recipient_id: Union[str, int],
) -> None:
    """Executes domain logic for an operation using agnostic notification delivery."""
    import os

    notifier = _resolve_notifier(bot_or_notifier)
    rec_str = str(recipient_id)

    if operacion == "registrar_movimiento":
        from logic.financiero import AgenteFinanciero

        spreadsheet_id = str(
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        resultado = agente.registrar_movimiento(payload)
        notifier.send_message(rec_str, resultado)

    elif operacion == "create_debt":
        from logic.financiero import create_debt

        debt_id = create_debt(
            entity=payload["entidad"],
            concept=payload["concepto"],
            total_amount=payload["monto"],
            quotas=payload["cuotas"],
            first_due_date=payload["fecha"],
        )
        notifier.send_message(
            rec_str,
            f"✅ Deuda '{payload['concepto']}' registrada con éxito. ID: `{debt_id}`",
            parse_mode="Markdown",
        )

    elif operacion == "register_payment":
        from logic.financiero import register_payment

        register_payment(
            debt_id=payload["debt_id"],
            amount=payload["amount"],
            date=payload["date"],
            tasa_iva=payload.get("tasa_iva", "Exento"),
        )
        monto_str = "{:,}".format(payload["amount"]).replace(",", ".")
        notifier.send_message(
            rec_str,
            f"✅ Abono de Gs. {monto_str} registrado para la deuda `{payload['debt_id']}`.",
            parse_mode="Markdown",
        )

    elif operacion == "crear_aviso_calendar":
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id_cal = str(os.getenv("SPREADSHEET_ID") or "")
        agente_excel = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id_cal)
        resultado = agente_excel.guardar_aviso_calendar(payload)
        notifier.send_message(rec_str, resultado, parse_mode="Markdown")

    elif operacion == "generar_reporte":
        from logic.pdf_service import PDFService

        tipo = payload.get("tipo", "financiero")
        if tipo == "financiero":
            from logic.financiero import AgenteFinanciero

            spreadsheet_id = str(
                os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
            )
            agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
            datos, error = agente.preparar_datos_reporte()
        else:
            from logic.logic import AgenteAutonomoHoras

            spreadsheet_id_cal = str(os.getenv("SPREADSHEET_ID") or "")
            agente_excel = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id_cal)
            nombre_hoja = payload.get("nombre_hoja") or payload.get("hoja")
            descuento = float(payload.get("descuento", 0))
            incluir_iva = bool(payload.get("incluir_iva", False))
            datos, error = agente_excel.preparar_datos_reporte(
                nombre_hoja=nombre_hoja,
                descuento=descuento,
                incluir_iva=incluir_iva,
            )

        if error:
            notifier.send_message(rec_str, f"❌ Error generando reporte: {error}")
            return

        ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)
        if ruta_pdf and Path(ruta_pdf).exists():
            notifier.send_document(
                rec_str,
                ruta_pdf,
                caption=f"📊 {msg_pdf}",
                visible_file_name=Path(ruta_pdf).name,
            )
        else:
            notifier.send_message(
                rec_str, msg_pdf or "❌ No se pudo generar el archivo PDF."
            )

    elif operacion == "procesar_mensaje_whatsapp":
        text_content = payload.get("text", "").strip()
        push_name = payload.get("push_name") or "Usuario"
        lower_text = text_content.lower()

        # 1. Comandos de saludo / ayuda básica
        greetings = {
            "hola",
            "buenas",
            "buenas tardes",
            "buenas noches",
            "buen dia",
            "buenos dias",
            "start",
            "/start",
            "help",
            "ayuda",
            "menu",
            "/menu",
        }
        if lower_text in greetings:
            response_msg = (
                f"👋 ¡Hola {push_name}! Soy Gamma Bot.\n\n"
                f"Puedes registrar tus finanzas enviándome mensajes en lenguaje natural:\n\n"
                f"🔹 *Gastos:*\n"
                f"• 'Gasto 45.000 almuerzo en Don Vito'\n"
                f"• '15k en biggie pan y leche'\n"
                f"• 'Pague 120.000 combustible en Petrobras'\n\n"
                f"🔹 *Ingresos:*\n"
                f"• 'Ingreso 2.500.000 cobro de cliente'\n"
                f"• 'Cobré 1500000 sueldo'\n\n"
                f"¡Escribe tu movimiento y lo registraré automáticamente!"
            )
            notifier.send_message(rec_str, response_msg)
            return

        # 2. Procesamiento con FinanceNLParser
        from src.utils.nlp_parser import FinanceNLParser

        parsed = FinanceNLParser.parse(text_content)

        if parsed.valido and parsed.monto > 0:
            if parsed.monto.is_integer():
                monto_fmt = f"{int(parsed.monto):,}".replace(",", ".") + " Gs"
            else:
                monto_fmt = (
                    f"{parsed.monto:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )

            # Persistir en Google Sheets / repositorio contable
            try:
                from repositories.sheets_repository import SheetsRepository
                from logic.logic import get_now_py

                repo = SheetsRepository()
                ws = repo._get_sheet("Libro_Diario")
                if ws:
                    ahora = get_now_py()
                    total_int = int(parsed.monto)
                    monto_gravado = round(total_int / 1.1)
                    monto_iva = total_int - monto_gravado
                    nueva_fila = [
                        ahora.strftime("%d/%m/%Y"),
                        parsed.tipo_movimiento,
                        parsed.proveedor_cliente,
                        "S/N",
                        str(monto_gravado),
                        str(monto_iva),
                        str(total_int),
                        parsed.categoria,
                        "No Legal",
                        "",
                        ahora.strftime("%m/%Y"),
                        "",
                        "10%",
                        str(monto_gravado),
                        str(monto_iva),
                        "10%",
                    ]
                    ws.append_row(nueva_fila)

                try:
                    from repositories.sheets_repository import _sheets_cache

                    _sheets_cache.clear()
                except Exception:
                    pass
            except Exception as e_sheet:
                logger.warning(
                    f"Error persistiendo movimiento en Google Sheets: {e_sheet}"
                )

            response_msg = (
                f"✅ *{parsed.tipo_movimiento} Registrado*\n\n"
                f"💰 *Monto:* {monto_fmt}\n"
                f"🏷️ *Categoría:* {parsed.categoria}\n"
                f"🏢 *Comercio/Cliente:* {parsed.proveedor_cliente}\n"
                f"📝 *Detalle:* {parsed.descripcion}"
            )
            notifier.send_message(rec_str, response_msg)

            if parsed.tipo_movimiento.lower() == "gasto":
                try:
                    from services.presupuesto_service import (
                        despachar_alerta_presupuestaria_proactiva,
                    )

                    despachar_alerta_presupuestaria_proactiva(
                        categoria=parsed.categoria,
                        monto_nuevo=float(parsed.monto),
                        recipient_id=rec_str,
                        channel="whatsapp",
                    )
                except Exception as e_al:
                    logger.debug(
                        f"Error evaluando alerta presupuestaria WhatsApp: {e_al}"
                    )
        else:
            if any(char.isdigit() for char in text_content):
                response_msg = (
                    "🤔 No pude interpretar el movimiento con certeza.\n\n"
                    "Por favor especifica el monto y el concepto. Ejemplos:\n"
                    "• 'Gasto 50.000 combustible en Shell'\n"
                    "• 'Ingreso 1500000 cobro de cliente'\n"
                    "• '15k en biggie pan y leche'"
                )
            else:
                response_msg = (
                    f"👋 Hola {push_name}, recibí tu mensaje: '{text_content}'\n\n"
                    f"Para registrar un gasto o ingreso, puedes escribir por ejemplo:\n"
                    f"• 'Gasto 45.000 almuerzo en Don Vito'\n"
                    f"• 'Ingreso 500k adelanto sueldo'"
                )
            notifier.send_message(rec_str, response_msg)

    elif operacion == "enviar_notificacion":
        mensaje = payload.get("mensaje", "")
        titulo = payload.get("titulo")
        parse_mode = payload.get("parse_mode", "Markdown")
        extra_kwargs: Dict[str, Any] = {}
        if titulo:
            extra_kwargs["title"] = titulo
        notifier.send_message(rec_str, mensaje, parse_mode=parse_mode, **extra_kwargs)

    else:
        logger.warning(f"Operación desconocida en cola: '{operacion}'")
        notifier.send_message(rec_str, f"✅ Trabajo '{operacion}' completado.")


def enqueue(
    recipient_id: Union[str, int],
    operacion: str,
    payload: Dict[str, Any],
    sync_fallback_or_channel: Union[bool, str] = False,
    bot: Any = None,
    channel: str = "telegram",
    notifier: Optional[INotificationPort] = None,
    sync_fallback: Optional[bool] = None,
) -> int:
    """Inserts a new job into the queue, supporting multi-channel dispatch and fallback.

    Args:
        recipient_id: Telegram chat ID or multi-channel recipient identifier.
        operacion: Name of domain operation.
        payload: Dictionary payload for the operation.
        sync_fallback_or_channel: Legacy sync_fallback bool or channel string.
        bot: Optional Telegram bot instance for legacy synchronous fallback.
        channel: Target notification channel ('telegram', 'whatsapp', etc.).
        notifier: Optional custom INotificationPort instance.
        sync_fallback: Explicit bool flag for synchronous fallback execution.

    Returns:
        Job ID, or 0 if executed synchronously via fallback.
    """
    if isinstance(sync_fallback_or_channel, str):
        target_channel = sync_fallback_or_channel
        is_sync_fallback = bool(sync_fallback) if sync_fallback is not None else False
    else:
        target_channel = channel
        is_sync_fallback = (
            sync_fallback
            if sync_fallback is not None
            else bool(sync_fallback_or_channel)
        )

    actual_notifier = notifier or (_resolve_notifier(bot) if bot is not None else None)
    target_bot_or_notifier = bot if bot is not None else actual_notifier

    if is_sync_fallback and target_bot_or_notifier is not None:
        try:
            despachar_trabajo(target_bot_or_notifier, operacion, payload, recipient_id)
            logger.info(
                f"Executed job synchronously (sync_fallback) for recipient_id {recipient_id}, operacion {operacion}"
            )
            return 0
        except Exception as e:
            logger.error(f"Error in sync_fallback execution: {e}")
            try:
                if actual_notifier is not None:
                    actual_notifier.send_message(
                        str(recipient_id),
                        f"❌ Ocurrió un error al procesar tu reporte: {e}. Se reintentará en segundo plano.",
                    )
                elif bot is not None:
                    bot.send_message(
                        recipient_id,
                        f"❌ Ocurrió un error al procesar tu reporte: {e}. Se reintentará en segundo plano.",
                    )
            except Exception:
                pass

    try:
        conn = get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                payload_str = json.dumps(payload)
                now = int(time.time())
                recipient_str = str(recipient_id)

                try:
                    chat_id_val = int(recipient_id)
                except (ValueError, TypeError):
                    chat_id_val = 0

                cursor.execute("PRAGMA table_info(queue);")
                cols = {row["name"] for row in cursor.fetchall()}

                if "recipient_id" in cols and "channel" in cols:
                    cursor.execute(
                        "INSERT INTO queue (recipient_id, channel, chat_id, operacion, "
                        "payload_json, estado, creado_at, next_retry) "
                        "VALUES (?, ?, ?, ?, ?, 'pendiente', ?, ?)",
                        (
                            recipient_str,
                            target_channel,
                            chat_id_val,
                            operacion,
                            payload_str,
                            now,
                            now,
                        ),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO queue (chat_id, operacion, payload_json, estado, creado_at, next_retry) "
                        "VALUES (?, ?, ?, 'pendiente', ?, ?)",
                        (chat_id_val, operacion, payload_str, now, now),
                    )

                job_id = int(cursor.lastrowid or 0)
                logger.info(
                    f"Enqueued job {job_id} for recipient_id {recipient_id} [{target_channel}], operacion {operacion}"
                )
                return job_id
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error enqueueing job: {e}")
        if target_bot_or_notifier is not None:
            try:
                despachar_trabajo(
                    target_bot_or_notifier, operacion, payload, recipient_id
                )
                logger.info(
                    f"Fallback síncrono exitoso tras error de encolado para job {operacion}"
                )
                return 0
            except Exception as e2:
                logger.error(f"Error en fallback síncrono secundario: {e2}")
        return -1


def get_pending_count() -> int:
    """Returns the number of pending jobs in the queue."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM queue WHERE estado = 'pendiente'")
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        logger.error(f"Error getting pending count: {e}")
        return 0
    finally:
        conn.close()


def procesar_trabajos_pendientes(
    bot: Any = None,
    dispatcher: Optional[NotificationDispatcher] = None,
) -> int:
    """Processes pending jobs in the queue with atomic transactions and explicit logging."""
    conn = get_connection()
    procesados = 0
    try:
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(queue);")
        cols = {row["name"] for row in cursor.fetchall()}

        if "recipient_id" in cols and "channel" in cols:
            cursor.execute(
                "SELECT id, recipient_id, channel, chat_id, operacion, payload_json, reintentos FROM queue "
                "WHERE estado = 'pendiente' AND next_retry <= ? ORDER BY creado_at ASC LIMIT 10",
                (now,),
            )
        else:
            cursor.execute(
                "SELECT id, chat_id, operacion, payload_json, reintentos FROM queue "
                "WHERE estado = 'pendiente' AND next_retry <= ? ORDER BY creado_at ASC LIMIT 10",
                (now,),
            )
        jobs = cursor.fetchall()

        active_dispatcher = dispatcher
        if active_dispatcher is None:
            active_dispatcher = create_default_dispatcher(bot=bot)

        for job in jobs:
            job_id = job["id"]
            chat_id = job["chat_id"] if "chat_id" in job.keys() else 0
            recipient_id = (
                job["recipient_id"]
                if "recipient_id" in job.keys() and job["recipient_id"]
                else str(chat_id)
            )
            channel = (
                job["channel"]
                if "channel" in job.keys() and job["channel"]
                else "telegram"
            )
            operacion = job["operacion"]
            payload_json = job["payload_json"]
            reintentos = job["reintentos"]

            target_rec = chat_id if (bot is not None and chat_id) else recipient_id

            logger.info(
                f"Iniciando job_id={job_id} operacion='{operacion}' "
                f"recipient_id={recipient_id} channel={channel}"
            )
            try:
                payload = json.loads(payload_json)

                if bot is not None:
                    despachar_trabajo(bot, operacion, payload, target_rec)
                elif active_dispatcher.has_channel(channel):
                    adapter = active_dispatcher.get_adapter(channel)
                    despachar_trabajo(adapter, operacion, payload, recipient_id)
                else:
                    adapter = active_dispatcher.get_adapter()
                    despachar_trabajo(adapter, operacion, payload, recipient_id)

                with conn:
                    conn.execute(
                        "UPDATE queue SET estado = 'completado' WHERE id = ?",
                        (job_id,),
                    )
                procesados += 1
                logger.info(
                    f"Trabajo completado exitosamente job_id={job_id} operacion='{operacion}'"
                )

            except Exception as e:
                reintentos += 1
                logger.error(
                    f"Error procesando trabajo job_id={job_id} (intento {reintentos}): {e}"
                )
                with conn:
                    if reintentos >= 5:
                        conn.execute(
                            "UPDATE queue SET estado = 'fallido', reintentos = ? WHERE id = ?",
                            (reintentos, job_id),
                        )
                        logger.error(
                            f"Trabajo marcado como fallido tras 5 reintentos job_id={job_id}"
                        )
                    else:
                        backoff = (2**reintentos) * 10
                        next_retry = now + backoff
                        conn.execute(
                            "UPDATE queue SET reintentos = ?, next_retry = ? WHERE id = ?",
                            (reintentos, next_retry, job_id),
                        )
    except Exception as e:
        logger.error(f"Error en procesar_trabajos_pendientes: {e}")
    finally:
        conn.close()

    return procesados
