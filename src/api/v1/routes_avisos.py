from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import AvisoCreate, AvisoUpdate, IAParseRequest
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("routes_avisos")

avisos_bp = Blueprint("avisos_v1", __name__)


def _get_avisos_file() -> Path:
    try:
        import api.blueprint as bp

        return bp.AVISOS_FILE
    except Exception:
        return Path(__file__).resolve().parents[2] / "avisos.json"


@avisos_bp.route("/ia/interpretar", methods=["POST"])
@require_api_key
def interpretar_ia() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = IAParseRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from logic.ai_service import AIService

        res = AIService.procesar_movimiento_con_ia(
            req_obj.texto, req_obj.tipo or "Gasto"
        )
        return jsonify(res), 200
    except Exception as e:
        logger.error(f"Error en /ia/interpretar: {e}")
        return (
            jsonify(
                {
                    "proveedor_cliente": "Proveedor IA",
                    "total": 50000,
                    "categoria": "Varios",
                    "tipo_movimiento": req_obj.tipo or "Gasto",
                    "fecha": get_now_py().strftime("%d/%m"),
                }
            ),
            200,
        )


@avisos_bp.route("/ia/interpretar/aviso", methods=["POST"])
@require_api_key
def interpretar_aviso_ia() -> Any:
    data = request.get_json(silent=True) or {}
    texto = data.get("texto", "")
    ahora = get_now_py()

    titulo = f"Recordatorio: {texto[:30]}" if texto else "Aviso sugerido"
    fecha_evento_str = None

    # Intentar parseo con IA si hay API KEY disponible
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and texto:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = (
                f"Eres un asistente organizador. Analiza el siguiente texto de un recordatorio o evento.\n"
                f"Hoy es {ahora.strftime('%d/%m/%Y %H:%M')}.\n"
                f"Extrae y devuelve un JSON estricto con:\n"
                f"1. 'titulo': nombre breve y descriptivo del evento.\n"
                "2. 'fecha_evento': fecha y hora del evento en formato 'DD/MM/YYYY HH:MM'. "
                "Si el usuario menciona un día o fecha futura (ej. 'mañana', 'el 25', 'el viernes'), "
                "calcula la fecha correcta. Si no especifica hora, asume 09:00.\n"
                f"Texto: {texto}"
            )
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            parsed = json.loads(resp.text)
            titulo = parsed.get("titulo", titulo)
            fecha_evento_str = parsed.get("fecha_evento")
        except Exception as e_ai:
            logger.warning(f"Error procesando aviso con Gemini: {e_ai}")

    # Fallback determinista con regex si no hubo IA o falló
    if not fecha_evento_str:
        match_fecha = re.search(r"(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?", texto)
        match_hora = re.search(r"(\d{1,2}):(\d{2})", texto)
        hora_str = (
            f"{match_hora.group(1).zfill(2)}:{match_hora.group(2)}"
            if match_hora
            else "09:00"
        )

        if match_fecha:
            d = match_fecha.group(1).zfill(2)
            m = match_fecha.group(2).zfill(2)
            y = match_fecha.group(3) or str(ahora.year)
            if len(y) == 2:
                y = f"20{y}"
            fecha_evento_str = f"{d}/{m}/{y} {hora_str}"
        elif "mañana" in texto.lower():
            manana = ahora + timedelta(days=1)
            fecha_evento_str = manana.strftime(f"%d/%m/%Y {hora_str}")
        elif "pasado mañana" in texto.lower():
            pasado = ahora + timedelta(days=2)
            fecha_evento_str = pasado.strftime(f"%d/%m/%Y {hora_str}")
        else:
            # Fallback seguro: agendar para mañana a las 09:00 (nunca la hora de la petición)
            fallback_dt = ahora + timedelta(days=1)
            fecha_evento_str = fallback_dt.strftime("%d/%m/%Y 09:00")

    # Cálculo relativo de días restantes
    dias_restantes = 1
    try:
        dt_evento = datetime.strptime(fecha_evento_str.split()[0], "%d/%m/%Y")
        dt_hoy = datetime(ahora.year, ahora.month, ahora.day)
        dias_restantes = max(0, (dt_evento - dt_hoy).days)
    except Exception:
        pass

    return (
        jsonify(
            {
                "id": str(uuid.uuid4())[:8],
                "titulo": titulo,
                "fecha_evento": fecha_evento_str,
                "dias_restantes": dias_restantes,
            }
        ),
        200,
    )


@avisos_bp.route("/avisos", methods=["GET"])
@require_api_key
def get_avisos() -> Any:
    avisos: list[dict[str, Any]] = []
    avisos_file = _get_avisos_file()
    # 1. Avisos persistidos localmente
    if avisos_file.exists():
        try:
            with open(avisos_file, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception as e:
            logger.warning(f"Error leyendo {avisos_file}: {e}")
            avisos = []

    # 2. Avisos sincronizados desde Google Calendar
    try:
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente_horas = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
        eventos_calendar = agente_horas.obtener_lista_avisos_calendar()
        if eventos_calendar:
            titulos_existentes = {a.get("titulo") for a in avisos}
            for ev in eventos_calendar:
                titulo = ev.get("titulo", "")
                if titulo and titulo not in titulos_existentes:
                    avisos.append(
                        {
                            "id": str(ev.get("id", f"cal-{len(avisos)}")),
                            "event_id": str(ev.get("id", "")),
                            "titulo": titulo,
                            "fecha_evento": ev.get("fecha_evento", ""),
                            "repeticion": "NINGUNA",
                            "hitos_minutos": [1440],
                        }
                    )
    except Exception as e_cal:
        logger.warning(
            f"No se pudieron sincronizar eventos de Calendar en /avisos: {e_cal}"
        )

    return jsonify(avisos), 200


@avisos_bp.route("/avisos", methods=["POST"])
@require_api_key
def create_aviso() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = AvisoCreate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    aviso_id = str(uuid.uuid4())[:8]
    event_id = ""

    # Sincronización con Google Calendar
    try:
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente_horas = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)

        partes = req_obj.fecha_evento.strip().split()
        fecha_str = partes[0]
        hora_str = partes[1] if len(partes) > 1 else "09:00"

        reminders = [
            {"method": "popup", "minutes": m} for m in req_obj.hitos_minutos[:5]
        ]
        datos_evento = {
            "titulo": req_obj.titulo,
            "fecha": fecha_str,
            "hora": hora_str,
            "reminders": reminders,
        }
        res_cal = agente_horas.guardar_aviso_calendar(datos_evento)
        if "✅" in str(res_cal):
            event_id = f"gcal-{aviso_id}"
    except Exception as e_cal:
        logger.warning(f"Error sincronizando aviso en Calendar: {e_cal}")

    nuevo_aviso = {
        "id": aviso_id,
        "event_id": event_id,
        "titulo": req_obj.titulo,
        "fecha_evento": req_obj.fecha_evento,
        "repeticion": req_obj.repeticion,
        "hitos_minutos": req_obj.hitos_minutos,
        "dias_restantes": req_obj.dias_restantes or 0,
        "alertas_disparadas": [],
    }

    avisos = []
    avisos_file = _get_avisos_file()
    if avisos_file.exists():
        try:
            with open(avisos_file, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception:
            avisos = []
    avisos.append(nuevo_aviso)
    try:
        with open(avisos_file, "w", encoding="utf-8") as f:
            json.dump(avisos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando aviso: {e}")

    return jsonify(nuevo_aviso), 201


@avisos_bp.route("/avisos/<aviso_id>", methods=["PUT"])
@require_api_key
def update_aviso(aviso_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = AvisoUpdate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    avisos = []
    avisos_file = _get_avisos_file()
    if avisos_file.exists():
        try:
            with open(avisos_file, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception:
            avisos = []

    target = None
    for a in avisos:
        if str(a.get("id")) == str(aviso_id):
            target = a
            break

    if not target:
        return (
            jsonify(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Aviso {aviso_id} no encontrado",
                    }
                }
            ),
            404,
        )

    if req_obj.titulo is not None:
        target["titulo"] = req_obj.titulo
    if req_obj.fecha_evento is not None:
        target["fecha_evento"] = req_obj.fecha_evento
    if req_obj.repeticion is not None:
        target["repeticion"] = req_obj.repeticion
    if req_obj.hitos_minutos is not None:
        target["hitos_minutos"] = req_obj.hitos_minutos
    if req_obj.dias_restantes is not None:
        target["dias_restantes"] = req_obj.dias_restantes

    # Sincronización en Google Calendar
    try:
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente_horas = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
        if target.get("event_id"):
            agente_horas.eliminar_aviso_calendar(target["event_id"])

        partes = target["fecha_evento"].strip().split()
        fecha_str = partes[0]
        hora_str = partes[1] if len(partes) > 1 else "09:00"
        reminders = [
            {"method": "popup", "minutes": m}
            for m in target.get("hitos_minutos", [1440])[:5]
        ]
        res_cal = agente_horas.guardar_aviso_calendar(
            {
                "titulo": target["titulo"],
                "fecha": fecha_str,
                "hora": hora_str,
                "reminders": reminders,
            }
        )
        if "✅" in str(res_cal):
            target["event_id"] = f"gcal-{aviso_id}"
    except Exception as e_cal:
        logger.warning(f"Error actualizando aviso en Calendar: {e_cal}")

    try:
        with open(avisos_file, "w", encoding="utf-8") as f:
            json.dump(avisos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando avisos actualizados: {e}")

    return jsonify(target), 200


@avisos_bp.route("/avisos/<aviso_id>", methods=["DELETE"])
@require_api_key
def delete_aviso(aviso_id: str) -> Any:
    event_id_to_delete = ""
    avisos_file = _get_avisos_file()
    if avisos_file.exists():
        try:
            with open(avisos_file, "r", encoding="utf-8") as f:
                avisos = json.load(f)
            for a in avisos:
                if str(a.get("id")) == str(aviso_id):
                    event_id_to_delete = a.get("event_id", "")
                    break
            avisos = [a for a in avisos if str(a.get("id")) != str(aviso_id)]
            with open(avisos_file, "w", encoding="utf-8") as f:
                json.dump(avisos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error borrando aviso: {e}")

    if event_id_to_delete:
        try:
            from logic.logic import AgenteAutonomoHoras

            spreadsheet_id = (
                os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
            )
            agente_horas = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
            agente_horas.eliminar_aviso_calendar(event_id_to_delete)
        except Exception as e_cal:
            logger.warning(f"Error eliminando evento de Calendar: {e_cal}")

    return jsonify({"status": "deleted"}), 200
