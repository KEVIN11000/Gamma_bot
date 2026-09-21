from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict

from logger_config import setup_logger

logger = setup_logger("worker")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "cola.db"


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database with timeout=15.0 and WAL mode."""
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
    except Exception:
        pass
    return conn


def init_db() -> None:
    """Initializes the database schema for the queue."""
    try:
        conn = get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        operacion TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        estado TEXT NOT NULL DEFAULT 'pendiente',
                        reintentos INTEGER NOT NULL DEFAULT 0,
                        next_retry INTEGER NOT NULL DEFAULT 0,
                        creado_at INTEGER NOT NULL
                    )
                    """)
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error initializing DB: {e}")


# Initialize DB on module import
init_db()


def despachar_trabajo(
    bot: Any, operacion: str, payload: Dict[str, Any], chat_id: int
) -> None:
    """Executes the specific domain logic for an enqueued operation."""
    import os

    if operacion == "registrar_movimiento":
        from logic.financiero import AgenteFinanciero

        spreadsheet_id = str(
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        resultado = agente.registrar_movimiento(payload)
        bot.send_message(chat_id, resultado)

    elif operacion == "create_debt":
        from logic.financiero import create_debt

        debt_id = create_debt(
            entity=payload["entidad"],
            concept=payload["concepto"],
            total_amount=payload["monto"],
            quotas=payload["cuotas"],
            first_due_date=payload["fecha"],
        )
        bot.send_message(
            chat_id,
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
        bot.send_message(
            chat_id,
            f"✅ Abono de Gs. {monto_str} registrado para la deuda `{payload['debt_id']}`.",
            parse_mode="Markdown",
        )

    elif operacion == "crear_aviso_calendar":
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id_cal = str(os.getenv("SPREADSHEET_ID") or "")
        agente_excel = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id_cal)
        resultado = agente_excel.guardar_aviso_calendar(payload)
        bot.send_message(chat_id, resultado, parse_mode="Markdown")

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
            nombre_hoja = payload.get("nombre_hoja")
            descuento = float(payload.get("descuento", 0))
            incluir_iva = bool(payload.get("incluir_iva", False))
            datos, error = agente_excel.preparar_datos_reporte(
                nombre_hoja=nombre_hoja, descuento=descuento, incluir_iva=incluir_iva
            )

        if error:
            bot.send_message(chat_id, f"❌ Error generando reporte: {error}")
            return

        ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)
        if ruta_pdf and Path(ruta_pdf).exists():
            with open(ruta_pdf, "rb") as f:
                bot.send_document(
                    chat_id,
                    f,
                    caption=f"📊 {msg_pdf}",
                    visible_file_name=Path(ruta_pdf).name,
                )
        else:
            bot.send_message(
                chat_id, msg_pdf or "❌ No se pudo generar el archivo PDF."
            )

    else:
        logger.warning(f"Operación desconocida en cola: '{operacion}'")
        bot.send_message(chat_id, f"✅ Trabajo '{operacion}' completado.")


def enqueue(
    chat_id: int,
    operacion: str,
    payload: Dict[str, Any],
    sync_fallback: bool = False,
    bot: Any = None,
) -> int:
    """Inserts a new job into the queue, with optional synchronous fallback.

    Args:
        chat_id: The Telegram chat ID.
        operacion: The operation to perform.
        payload: A dictionary containing the job data.
        sync_fallback: If True, executes the job synchronously.
        bot: Optional bot instance for synchronous fallback execution.

    Returns:
        The ID of the inserted job, or 0 if executed synchronously via fallback.
    """
    if sync_fallback and bot is not None:
        try:
            despachar_trabajo(bot, operacion, payload, chat_id)
            logger.info(
                f"Executed job synchronously (sync_fallback) for chat_id {chat_id}, operacion {operacion}"
            )
            return 0
        except Exception as e:
            logger.error(f"Error in sync_fallback execution: {e}")

    try:
        conn = get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                payload_str = json.dumps(payload)
                now = int(time.time())
                cursor.execute(
                    "INSERT INTO queue (chat_id, operacion, payload_json, estado, creado_at, next_retry) "
                    "VALUES (?, ?, ?, 'pendiente', ?, ?)",
                    (chat_id, operacion, payload_str, now, now),
                )
                job_id = int(cursor.lastrowid or 0)
                logger.info(
                    f"Enqueued job {job_id} for chat_id {chat_id}, operacion {operacion}"
                )
                return job_id
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error enqueueing job: {e}")
        if bot is not None:
            try:
                despachar_trabajo(bot, operacion, payload, chat_id)
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


def procesar_trabajos_pendientes(bot: Any) -> int:
    """Processes pending jobs in the queue with atomic transactions and explicit logging."""
    conn = get_connection()
    procesados = 0
    try:
        now = int(time.time())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, chat_id, operacion, payload_json, reintentos FROM queue "
            "WHERE estado = 'pendiente' AND next_retry <= ? ORDER BY creado_at ASC LIMIT 10",
            (now,),
        )
        jobs = cursor.fetchall()

        for job in jobs:
            job_id = job["id"]
            chat_id = job["chat_id"]
            operacion = job["operacion"]
            payload_json = job["payload_json"]
            reintentos = job["reintentos"]

            logger.info(
                f"Iniciando procesamiento job_id={job_id} operacion='{operacion}' chat_id={chat_id}"
            )
            try:
                payload = json.loads(payload_json)
                despachar_trabajo(bot, operacion, payload, chat_id)

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
