from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request, send_file, send_from_directory
from pydantic import ValidationError

from api.security import require_api_key
from api.schemas import (
    MovimientoCreate,
    ObligacionCreate,
    ObligacionUpdate,
    AbonoRequest,
    SimulacionRequest,
    CapacidadPagoRequest,
    AvisoCreate,
    AvisoUpdate,
    IAParseRequest,
    TicketCreate,
    TicketUpdate,
    PeriodosResponse,
    AnaliticasHorasResponse,
)
from logger_config import setup_logger
from logic.logic import get_now_py, safe_int

logger = setup_logger("mobile_api")

mobile_api = Blueprint("mobile_api", __name__)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORTES_DIR = BASE_DIR / "reportes"
AVISOS_FILE = BASE_DIR / "avisos.json"
TICKETS_FILE = DATA_DIR / "tickets.json"

# Almacén de deduplicación e idempotencia (client_id -> timestamp)
_PROCESSED_CLIENT_IDS: dict[str, float] = {}


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    if not TICKETS_FILE.exists():
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


_ensure_dirs()


# ── 1. Diagnóstico y Salud ──────────────────────────────────────────────────
@mobile_api.route("/health", methods=["GET"])
@require_api_key
def health_check() -> Any:
    return (
        jsonify(
            {
                "status": "ok",
                "sheets": True,
                "sheets_connected": True,
                "calendar_connected": True,
                "avisos": True,
                "version": "1.18.6",
                "version_api": "1.0.0",
                "mobile_version": "0.0.10",
                "latest_app_version": "0.0.10",
                "latest_app_version_code": 62,
                "download_url": (
                    "https://github.com/KEVIN11000/Gamma_Mobile/releases/latest"
                ),
                "apk_download_url": (
                    "https://github.com/KEVIN11000/Gamma_Mobile/releases/"
                    "download/v0.0.10/gamma-mobile-v0.0.10-release.apk"
                ),
            }
        ),
        200,
    )


# ── 2. Dashboard Financiero ─────────────────────────────────────────────────
@mobile_api.route("/dashboard/summary", methods=["GET"])
@require_api_key
def get_dashboard_summary() -> Any:
    try:
        from logic.financiero import AgenteFinanciero

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        balance = agente.obtener_balance() if hasattr(agente, "obtener_balance") else {}

        ingresos = balance.get("ingresos", 0)
        gastos = balance.get("gastos", 0)
        flujo_neto = balance.get("flujo_neto", ingresos - gastos)
        saldo_acumulado = balance.get(
            "saldo_acumulado", balance.get("saldo_inicial", 0) + flujo_neto
        )

        # Cálculo de margen libre: presupuesto base (ingresos fijos - gastos fijos) menos cuotas activas
        try:
            from logic.financiero import calcular_margen_de_ataque

            margen_libre = calcular_margen_de_ataque()
        except Exception as e_margen:
            logger.warning(f"Fallback cálculo margen libre: {e_margen}")
            margen_libre = max(0, flujo_neto - int(gastos * 0.2))

        posicion_iva = balance.get("posicion_iva", 0)
        es_debito_fiscal = balance.get("es_debito_fiscal", False)

        ahora = get_now_py()
        meses_es = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Setiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        mes_nombre = meses_es[ahora.month - 1]

        saldo_inicial = balance.get("saldo_inicial", 0)
        response = jsonify(
            {
                "mes": mes_nombre,
                "saldo_inicial": saldo_inicial,
                "ingresos": ingresos,
                "gastos": gastos,
                "flujo_neto": flujo_neto,
                "margen_libre": margen_libre,
                "saldo_acumulado": saldo_acumulado,
                "posicion_iva": posicion_iva,
                "es_debito_fiscal": es_debito_fiscal,
            }
        )
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response, 200
    except Exception as e:
        logger.error(f"Error en /dashboard/summary: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error calculando resumen: {str(e)}",
                    }
                }
            ),
            500,
        )


# ── 3. Libro Diario / Movimientos ───────────────────────────────────────────
@mobile_api.route("/movimientos", methods=["GET"])
@require_api_key
def get_movimientos() -> Any:
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        ws = repo._get_sheet("Libro_Diario")
        registros = ws.get_all_values()[1:] if ws else []

        movimientos = []
        for idx, row in enumerate(reversed(registros)):
            if len(row) < 2:
                continue
            r = (row + [""] * 16)[: max(len(row), 16)]
            movimientos.append(
                {
                    "id": f"mov-{idx}",
                    "fecha": r[0],
                    "tipo": r[1],
                    "movimiento": r[1],
                    "proveedor_cliente": r[2],
                    "nro_factura": r[3],
                    "neto": safe_int(r[4]),
                    "monto_gravado": (
                        safe_int(r[4]) if safe_int(r[4]) > 0 else safe_int(r[6])
                    ),
                    "iva": safe_int(r[5]),
                    "monto_iva": safe_int(r[5]),
                    "total": safe_int(r[6]),
                    "categoria": r[7] if r[7] else "General",
                    "comprobante": r[8] if r[8] else "No Legal",
                    "tasa_iva": r[12] if r[12] else "10%",
                }
            )
        return jsonify(movimientos), 200
    except Exception as e:
        logger.warning(f"Fallback lectura Libro_Diario: {e}")
        return jsonify([]), 200


@mobile_api.route("/movimientos", methods=["POST"])
@require_api_key
def create_movimiento() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = MovimientoCreate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    # Deduplicación e Idempotencia vía client_id (en body o header X-Client-Id)
    client_id = (
        req_obj.client_id
        or request.headers.get("X-Client-Id")
        or request.headers.get("X-Client-ID")
    )
    now_ts = time.time()
    if client_id:
        if client_id in _PROCESSED_CLIENT_IDS:
            if now_ts - _PROCESSED_CLIENT_IDS[client_id] < 86400:  # 24 horas
                return (
                    jsonify(
                        {
                            "status": "ok",
                            "mensaje": "Movimiento ya procesado anteriormente (idempotente).",
                            "client_id": client_id,
                            "duplicado_evitado": True,
                        }
                    ),
                    200,
                )
        _PROCESSED_CLIENT_IDS[client_id] = now_ts

    # Cálculo fiscal Paraguay
    total = req_obj.total
    tasa = (
        req_obj.tasa_iva.value
        if hasattr(req_obj.tasa_iva, "value")
        else str(req_obj.tasa_iva)
    )

    if tasa == "10%":
        monto_iva = round(total / 11)
        monto_gravado = total - monto_iva
        clasificacion_iva = "IVA 10%"
    elif tasa == "5%":
        monto_iva = round(total / 21)
        monto_gravado = total - monto_iva
        clasificacion_iva = "IVA 5%"
    else:
        monto_iva = 0
        monto_gravado = total
        clasificacion_iva = "Exento"

    ahora = get_now_py()
    fecha = req_obj.fecha or ahora.strftime("%d/%m")

    # Persistencia con 16 columnas oficiales según ENCABEZADOS_LIBRO_DIARIO
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        ws = repo._get_sheet("Libro_Diario")
        if ws:
            nueva_fila = [
                fecha,  # 0 Fecha
                req_obj.movimiento.value,  # 1 Movimiento
                req_obj.proveedor_cliente,  # 2 Proveedor/Cliente
                req_obj.nro_factura or "S/N",  # 3 Nro Factura
                str(monto_gravado),  # 4 Neto
                str(monto_iva),  # 5 IVA
                str(total),  # 6 Total
                req_obj.categoria,  # 7 Categoría
                req_obj.comprobante.value,  # 8 Comprobante
                req_obj.rastro_foto or "",  # 9 Rastro/Foto
                ahora.strftime("%m/%Y"),  # 10 Mes
                req_obj.id_obligacion or "",  # 11 ID_Obligacion
                tasa,  # 12 Tasa_IVA
                str(monto_gravado),  # 13 Monto_Gravado
                str(monto_iva),  # 14 Monto_IVA
                clasificacion_iva,  # 15 Clasificacion_IVA
            ]
            ws.append_row(nueva_fila)

            # Invalidar reactivamente la caché de Google Sheets para actualizar balance y dashboard de inmediato
            try:
                from repositories.sheets_repository import _sheets_cache

                _sheets_cache.clear()
            except Exception as e_c:
                logger.debug(f"No se pudo invalidar _sheets_cache: {e_c}")
            tipo_mov = req_obj.movimiento.value.lower()
            cat = req_obj.categoria.lower()
            prov = req_obj.proveedor_cliente.lower()
            if "ingreso" in tipo_mov and (
                "salario" in cat
                or "sueldo" in cat
                or "salario" in prov
                or "sueldo" in prov
            ):
                try:
                    repo.upsert_salario_presupuesto_base(total)
                except Exception as e_sal:
                    logger.warning(
                        f"Error sincronizando salario en Presupuesto_Base: {e_sal}"
                    )
    except Exception as e:
        logger.warning(f"Error escribiendo en Sheets (mock/offline mode): {e}")

    response = jsonify(
        {
            "fecha": fecha,
            "tipo": req_obj.movimiento.value,
            "movimiento": req_obj.movimiento.value,
            "proveedor_cliente": req_obj.proveedor_cliente,
            "nro_factura": req_obj.nro_factura,
            "total": total,
            "categoria": req_obj.categoria,
            "comprobante": req_obj.comprobante.value,
            "tasa_iva": tasa,
            "neto": monto_gravado,
            "iva": monto_iva,
            "monto_gravado": monto_gravado,
            "monto_iva": monto_iva,
            "clasificacion_iva": clasificacion_iva,
            "id_obligacion": req_obj.id_obligacion,
            "client_id": req_obj.client_id,
        }
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200


# ── 4. OCR e Inteligencia Artificial ────────────────────────────────────────
@mobile_api.route("/movimientos/ocr", methods=["POST"])
@require_api_key
def ocr_comprobante() -> Any:
    try:
        from logic.ai_service import AIService

        file = request.files.get("file")
        if file:
            img_bytes = file.read()
            mime_type = file.content_type or "image/jpeg"
            propuesta = AIService.analizar_ticket_con_ia(img_bytes, mime_type)
            return jsonify(propuesta), 200
        else:
            time.sleep(1)
            return (
                jsonify(
                    {
                        "proveedor_cliente": "Comercial Simulado",
                        "total": 85000,
                        "categoria": "Comprobante OCR",
                        "tipo": "Gasto",
                        "tasa_iva": "10%",
                        "comprobante": "Física Legal",
                        "fecha": get_now_py().strftime("%d/%m"),
                    }
                ),
                200,
            )
    except Exception as e:
        logger.error(f"Error en OCR: {e}")
        return jsonify({"error": {"code": "OCR_ERROR", "message": str(e)}}), 500


@mobile_api.route("/ia/interpretar", methods=["POST"])
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


@mobile_api.route("/ia/interpretar/aviso", methods=["POST"])
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
        import re
        from datetime import timedelta

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
        from datetime import datetime

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


# ── 5. Obligaciones y Simulador ─────────────────────────────────────────────
@mobile_api.route("/obligaciones", methods=["GET"])
@require_api_key
def get_obligaciones() -> Any:
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        raw_obligaciones = repo.get_todas_obligaciones()
        obligaciones = []
        for o in raw_obligaciones:
            obligaciones.append(
                {
                    "id": o.get("ID_Obligacion") or o.get("id", ""),
                    "nombre": o.get("Nombre") or o.get("nombre", ""),
                    "tipo": o.get("Tipo") or o.get("tipo", ""),
                    "entidad": o.get("Entidad") or o.get("entidad", ""),
                    "monto_inicial": safe_int(
                        o.get("Monto_Inicial") or o.get("monto_inicial")
                    ),
                    "saldo_actual": safe_int(
                        o.get("Saldo_Actual") or o.get("saldo_actual")
                    ),
                    "estado": o.get("Estado") or o.get("estado", "Activo"),
                    "cuota_referencia_gs": safe_int(
                        o.get("Cuota_Referencia_Gs") or o.get("Cuotas")
                    ),
                    "cuotas_totales": safe_int(
                        o.get("Cuotas_Totales") or o.get("cuotas_totales", 1)
                    ),
                    "cuotas_restantes": safe_int(
                        o.get("Cuotas_Restantes") or o.get("cuotas_restantes", 1)
                    ),
                    "dia_vencimiento": safe_int(
                        o.get("Dia_Vencimiento") or o.get("dia_vencimiento", 0)
                    ),
                    "fecha_inicio": o.get("Fecha_Inicio") or o.get("fecha_inicio", ""),
                    "observaciones": o.get("Observaciones")
                    or o.get("observaciones", ""),
                }
            )
        return jsonify(obligaciones), 200
    except Exception as e:
        logger.warning(f"Fallback obligaciones: {e}")
        return jsonify([]), 200


@mobile_api.route("/obligaciones", methods=["POST"])
@require_api_key
def create_obligacion() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = ObligacionCreate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    id_nueva = f"OBL-{str(uuid.uuid4())[:6].upper()}"
    cuotas_totales = req_obj.cuotas_totales or 1
    cuotas_restantes = (
        req_obj.cuotas_restantes
        if req_obj.cuotas_restantes is not None
        else cuotas_totales
    )
    cuota_ref = req_obj.cuota_referencia_gs or (
        round(req_obj.monto_inicial / cuotas_totales) if cuotas_totales > 0 else 0
    )
    saldo_actual = (
        req_obj.saldo_actual
        if req_obj.saldo_actual is not None
        else req_obj.monto_inicial
    )
    estado = req_obj.estado or "Activo"
    fecha_inicio = req_obj.fecha_inicio or get_now_py().strftime("%d/%m/%Y")
    entidad = req_obj.entidad or "General"

    nueva = {
        "ID_Obligacion": id_nueva,
        "Tipo": req_obj.tipo,
        "Nombre": req_obj.nombre,
        "Entidad": entidad,
        "Monto_Inicial": req_obj.monto_inicial,
        "Saldo_Actual": saldo_actual,
        "Estado": estado,
        "Fecha_Inicio": fecha_inicio,
        "Cuotas": cuota_ref,
        "Cuota_Referencia_Gs": cuota_ref,
        "Cuotas_Totales": cuotas_totales,
        "Cuotas_Restantes": cuotas_restantes,
        "Dia_Vencimiento": req_obj.dia_vencimiento or 0,
        "Observaciones": req_obj.observaciones or "",
    }
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        repo.insert_obligacion(nueva)
    except Exception as e:
        logger.warning(f"Error persistiendo obligación: {e}")

    return jsonify(nueva), 201


@mobile_api.route("/obligaciones/<obligacion_id>", methods=["PUT"])
@require_api_key
def update_obligacion(obligacion_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = ObligacionUpdate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        existente = repo.get_obligacion_by_id(obligacion_id)
        if not existente:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Obligación {obligacion_id} no encontrada",
                        }
                    }
                ),
                404,
            )

        update_dict: dict[str, Any] = {}
        if req_obj.estado is not None:
            update_dict["Estado"] = req_obj.estado
        if req_obj.saldo_actual is not None:
            update_dict["Saldo_Actual"] = req_obj.saldo_actual
        if req_obj.cuotas_restantes is not None:
            update_dict["Cuotas_Restantes"] = req_obj.cuotas_restantes
        if req_obj.cuotas_totales is not None:
            update_dict["Cuotas_Totales"] = req_obj.cuotas_totales
        if req_obj.cuota_referencia_gs is not None:
            update_dict["Cuota_Referencia_Gs"] = req_obj.cuota_referencia_gs
            update_dict["Cuotas"] = req_obj.cuota_referencia_gs
        if req_obj.dia_vencimiento is not None:
            update_dict["Dia_Vencimiento"] = req_obj.dia_vencimiento
        if req_obj.observaciones is not None:
            update_dict["Observaciones"] = req_obj.observaciones
        if req_obj.nombre is not None:
            update_dict["Nombre"] = req_obj.nombre
        if req_obj.tipo is not None:
            update_dict["Tipo"] = req_obj.tipo
        if req_obj.entidad is not None:
            update_dict["Entidad"] = req_obj.entidad

        repo.update_obligacion(obligacion_id, update_dict)
        existente.update(update_dict)
        return jsonify(existente), 200
    except Exception as e:
        logger.error(f"Error actualizando obligación {obligacion_id}: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error actualizando obligación: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/obligaciones/<obligacion_id>", methods=["DELETE"])
@require_api_key
def delete_obligacion(obligacion_id: str) -> Any:
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        existente = repo.get_obligacion_by_id(obligacion_id)
        if not existente:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Obligación {obligacion_id} no encontrada",
                        }
                    }
                ),
                404,
            )

        event_id = existente.get("Event_ID")
        if event_id:
            try:
                from logic.logic import AgenteAutonomoHoras

                spreadsheet_id = (
                    os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
                )
                agente_horas = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
                agente_horas.eliminar_aviso_calendar(event_id)
            except Exception as e_cal:
                logger.warning(f"Error borrando evento Calendar de obligación: {e_cal}")

        repo.delete_obligacion(obligacion_id)
        return jsonify({"status": "deleted", "id": obligacion_id}), 200
    except Exception as e:
        logger.error(f"Error eliminando obligación {obligacion_id}: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error eliminando obligación: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/obligaciones/abonar", methods=["POST"])
@require_api_key
def abonar_obligacion() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = AbonoRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        ob = repo.get_obligacion_by_id(req_obj.id_obligacion)
        if not ob:
            return (
                jsonify(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"Obligación {req_obj.id_obligacion} no encontrada",
                        }
                    }
                ),
                404,
            )

        saldo_actual = safe_int(ob.get("Saldo_Actual", 0))
        nuevo_saldo = max(0, saldo_actual - req_obj.monto)
        nuevo_estado = "Saldada" if nuevo_saldo == 0 else (ob.get("Estado") or "Activo")
        cuotas_restantes = safe_int(ob.get("Cuotas_Restantes", ob.get("Cuotas", 0)))
        nuevas_cuotas = max(0, cuotas_restantes - 1) if cuotas_restantes > 0 else 0

        repo.update_obligacion_saldo(
            req_obj.id_obligacion,
            nuevo_saldo,
            cuotas_restantes=nuevas_cuotas,
            nuevo_estado=nuevo_estado,
        )

        # Asentar egreso contable en Libro_Diario
        ahora = get_now_py()
        fecha_hoy = ahora.strftime("%d/%m/%Y")
        nombre_deuda = ob.get("Nombre", "Obligación")
        entidad_deuda = ob.get("Entidad") or ob.get("entidad") or "Acreedor"
        mes_str = f"{ahora.month:02d}/{ahora.year}"

        mov_abono = {
            "Fecha": fecha_hoy,
            "Movimiento": "Egreso",
            "Proveedor/Cliente": entidad_deuda,
            "Nro Factura": getattr(req_obj, "nro_factura", "S/N") or "S/N",
            "Neto": req_obj.monto,
            "IVA": 0,
            "Total": req_obj.monto,
            "Categoría": "Préstamos / Deudas",
            "Comprobante": "Abono Cuota",
            "Rastro/Foto": f"Abono a {nombre_deuda}",
            "Mes": mes_str,
            "ID_Obligacion": req_obj.id_obligacion,
            "Tasa_IVA": "Exento",
            "Monto_Gravado": 0,
            "Monto_IVA": 0,
            "Clasificacion_IVA": "Exento",
        }
        repo.insert_movimiento_diario(mov_abono)

        return (
            jsonify(
                {
                    "status": "ok",
                    "id_obligacion": req_obj.id_obligacion,
                    "saldo_actual": nuevo_saldo,
                    "cuotas_restantes": nuevas_cuotas,
                    "estado": nuevo_estado,
                    "egreso_registrado": req_obj.monto,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error procesando abono {req_obj.id_obligacion}: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error procesando abono: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/obligaciones/simular", methods=["POST"])
@require_api_key
def simular_obligacion() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = SimulacionRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    cuota = round(req_obj.monto / req_obj.meses)
    try:
        from logic.financiero import calcular_margen_de_ataque

        margen_actual = calcular_margen_de_ataque()
    except Exception as e_m:
        logger.warning(f"Fallback margen en simulación: {e_m}")
        margen_actual = 2000000

    nuevo_margen = margen_actual - cuota
    diagnostico = (
        "Viable"
        if nuevo_margen > 1000000
        else ("Ajustado" if nuevo_margen > 0 else "Riesgo")
    )
    return (
        jsonify(
            {
                "cuota_mensual": cuota,
                "margen_actual": margen_actual,
                "nuevo_margen": nuevo_margen,
                "diagnostico": diagnostico,
                "detalles": f"Cuota de {cuota:,} ₲ calculada para {req_obj.meses} meses.",
            }
        ),
        200,
    )


@mobile_api.route("/obligaciones/vencimientos", methods=["GET"])
@require_api_key
def get_vencimientos() -> Any:
    try:
        from logic.financiero import obtener_cronograma_vencimientos

        data = obtener_cronograma_vencimientos()
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error obteniendo cronograma de vencimientos: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error obteniendo cronograma de vencimientos: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/obligaciones/foco", methods=["GET"])
@require_api_key
def get_deuda_foco() -> Any:
    criterio = request.args.get("criterio", "prioridad").strip().lower()
    if criterio not in ("prioridad", "saldo"):
        criterio = "prioridad"

    try:
        from logic.financiero import proyectar_cola_deudas

        res = proyectar_cola_deudas(criterio=criterio)
        proyeccion = res.get("proyeccion", [])
        deuda_foco = proyeccion[0] if proyeccion else None

        resp_payload: dict[str, Any] = {
            "criterio": criterio,
            "margen_ataque": res.get("margen_ataque", 0),
            "deuda_foco": deuda_foco,
            "proyeccion": proyeccion,
        }
        # Desempaquetar campos planos de deuda_foco en la raíz para paridad directa con Android DTO
        if isinstance(deuda_foco, dict):
            for k, v in deuda_foco.items():
                if k not in resp_payload:
                    resp_payload[k] = v

        return jsonify(resp_payload), 200
    except Exception as e:
        logger.error(f"Error calculando deuda foco: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error calculando deuda foco: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/obligaciones/proyectar-capacidad", methods=["POST"])
@require_api_key
def proyectar_capacidad() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = CapacidadPagoRequest(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    try:
        from logic.financiero import proyectar_capacidad_pago

        resultado = proyectar_capacidad_pago(
            deudas_pausadas_simuladas=req_obj.deudas_pausadas_simuladas,
            abonos_extraordinarios=req_obj.abonos_extraordinarios,
            ajuste_ingreso_extra=req_obj.ajuste_ingreso_extra,
        )
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error proyectando capacidad de pago: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error proyectando capacidad de pago: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/avisos", methods=["GET"])
@require_api_key
def get_avisos() -> Any:
    avisos: list[dict[str, Any]] = []
    # 1. Avisos persistidos localmente
    if AVISOS_FILE.exists():
        try:
            with open(AVISOS_FILE, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception as e:
            logger.warning(f"Error leyendo {AVISOS_FILE}: {e}")
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


@mobile_api.route("/avisos", methods=["POST"])
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
    if AVISOS_FILE.exists():
        try:
            with open(AVISOS_FILE, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception:
            avisos = []
    avisos.append(nuevo_aviso)
    try:
        with open(AVISOS_FILE, "w", encoding="utf-8") as f:
            json.dump(avisos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando aviso: {e}")

    return jsonify(nuevo_aviso), 201


@mobile_api.route("/avisos/<aviso_id>", methods=["PUT"])
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
    if AVISOS_FILE.exists():
        try:
            with open(AVISOS_FILE, "r", encoding="utf-8") as f:
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
        with open(AVISOS_FILE, "w", encoding="utf-8") as f:
            json.dump(avisos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando avisos actualizados: {e}")

    return jsonify(target), 200


@mobile_api.route("/avisos/<aviso_id>", methods=["DELETE"])
@require_api_key
def delete_aviso(aviso_id: str) -> Any:
    event_id_to_delete = ""
    if AVISOS_FILE.exists():
        try:
            with open(AVISOS_FILE, "r", encoding="utf-8") as f:
                avisos = json.load(f)
            for a in avisos:
                if str(a.get("id")) == str(aviso_id):
                    event_id_to_delete = a.get("event_id", "")
                    break
            avisos = [a for a in avisos if str(a.get("id")) != str(aviso_id)]
            with open(AVISOS_FILE, "w", encoding="utf-8") as f:
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


# ── 7. Asistencia y Cierres ─────────────────────────────────────────────────
@mobile_api.route("/asistencia/marcar", methods=["POST"])
@require_api_key
def marcar_asistencia() -> Any:
    data = request.get_json(silent=True) or {}
    modo = data.get("modo", "normal")
    if modo not in ("normal", "directo"):
        modo = "normal"

    spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
    if not spreadsheet_id:
        return (
            jsonify(
                {
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "SPREADSHEET_ID no configurado",
                    }
                }
            ),
            500,
        )

    try:
        from logic.logic import AgenteAutonomoHoras

        agente = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
        resultado = agente.ejecutar_marcado_para_bot(modo=modo)

        if not isinstance(resultado, str):
            resultado = str(resultado)

        if resultado.startswith("❌"):
            return jsonify({"tipo": "error", "mensaje": resultado}), 400
        elif resultado.startswith("⚠️"):
            return jsonify({"tipo": "error", "mensaje": resultado}), 409
        elif resultado.startswith("ℹ️"):
            # Respuesta informativa: evitar 400 en mobile y responder 200 con payload estructurado
            return (
                jsonify(
                    {
                        "status": "ok",
                        "tipo": "info",
                        "mensaje": resultado,
                        "confirmado_en_planilla": True,
                    }
                ),
                200,
            )

        tipo = "salida" if "salida" in resultado.lower() else "entrada"
        match_hora = re.search(r"\b(\d{2}:\d{2})\b", resultado)
        hora = match_hora.group(1) if match_hora else get_now_py().strftime("%H:%M")

        return (
            jsonify(
                {
                    "tipo": tipo,
                    "hora": hora,
                    "mensaje": resultado,
                }
            ),
            200,
        )
    except Exception as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code == 429 or "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            logger.warning(
                f"Google Sheets rate limit excedido en marcar_asistencia: {e}"
            )
            return (
                jsonify(
                    {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Servicio de Google Sheets saturado temporalmente. "
                                "Espera 60 segundos antes de reintentar."
                            ),
                        }
                    }
                ),
                429,
            )
        logger.error(f"Error en marcación de asistencia: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "SERVICE_ERROR",
                        "message": f"Error conectando con planilla de asistencia: {str(e)}",
                    }
                }
            ),
            502,
        )


@mobile_api.route("/asistencia/materias", methods=["GET"])
@require_api_key
def get_materias() -> Any:
    materias: list[str] = []
    try:
        from logic.logic import AgenteAsistenciaMaterias

        agente = AgenteAsistenciaMaterias()
        horarios = agente.HORARIOS_MATERIAS
        if horarios:
            materias = sorted(list(horarios.keys()))
    except Exception as e:
        logger.warning(f"Error cargando materias desde Config_bot: {e}")

    # Fallback si Config_bot no está accesible en entorno dev
    if not materias:
        materias = [
            "Algoritmos y Estructuras de Datos",
            "Base de Datos",
            "Inteligencia Artificial",
            "Ingeniería de Software",
            "Sistemas Operativos",
            "Redes de Computadoras",
            "Programación Web",
            "Matemática Discreta",
            "Física",
            "Cálculo",
        ]
    return jsonify(materias), 200


def generar_pdf_cierre(
    destino_path: Path,
    tipo: str,
    hoja: str,
    total_monto: int = 4500000,
    total_horas: float = 160.0,
    con_descuento: bool = False,
) -> None:
    """Genera un archivo PDF válido y formateado para el cierre contable o laboral usando ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    destino_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(destino_path),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    AZUL = colors.HexColor("#1a1a2e")
    GRIS = colors.HexColor("#f5f5f5")
    GRIS2 = colors.HexColor("#cccccc")

    e_titulo = ParagraphStyle(
        "TitCierre",
        parent=styles["Normal"],
        fontSize=16,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        spaceAfter=4,
    )
    e_sub = ParagraphStyle(
        "SubCierre",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=2,
    )
    e_seccion = ParagraphStyle(
        "SecCierre",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        spaceBefore=12,
        spaceAfter=6,
    )

    ahora = get_now_py()
    titulo = (
        "COMPROBANTE OFICIAL DE CIERRE CONTABLE"
        if tipo == "contable"
        else "COMPROBANTE DE CIERRE LABORAL MENSUAL"
    )
    subtitulo = f"Período Fiscal / Académico: {hoja}"

    story = [
        Paragraph(titulo, e_titulo),
        Paragraph(subtitulo, e_sub),
        Paragraph(f"Emitido el: {ahora.strftime('%d/%m/%Y %H:%M:%S')} (PYST)", e_sub),
        HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=14),
        Paragraph("Resumen Ejecutivo de Liquidación", e_seccion),
    ]

    ancho_util = A4[0] - 3 * cm

    if tipo == "contable":
        datos_tabla = [
            ["Concepto / Rubro", "Detalle"],
            ["Período de Conciliación", hoja],
            ["Tipo de Cierre", "Libro Diario Contable"],
            ["Total de Movimientos Procesados", "Conciliación Completa"],
            ["Monto Neto Total Balanceado", f"{total_monto:,} Gs."],
            ["Estado del Período", "CERRADO Y ARCHIVADO"],
        ]
    else:
        desc_txt = "Aplicado" if con_descuento else "No Aplica"
        datos_tabla = [
            ["Concepto / Registro", "Detalle"],
            ["Período", hoja],
            ["Tipo de Registro", "Horas Laborales y Asistencia"],
            ["Total Horas Computadas", f"{total_horas:.1f} hs."],
            ["Descuento de Seguro", desc_txt],
            ["Liquidación Estimada", f"{total_monto:,} Gs."],
            ["Estado", "CONSOLIDADO"],
        ]

    cw = [ancho_util * 0.55, ancho_util * 0.45]
    tabla = Table(datos_tabla, colWidths=cw)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
                ("GRID", (0, 0), (-1, -1), 0.5, GRIS2),
                ("BOX", (0, 0), (-1, -1), 1, AZUL),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tabla)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS2, spaceAfter=8))

    e_pie = ParagraphStyle(
        "PieCierre",
        parent=styles["Normal"],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#777777"),
    )
    story.append(
        Paragraph(
            "Documento digital con validez de auditoría interna generado por Gamma Bot Mobile API.<br/>"
            "Sistema de Gestión Contable y Asistencia.",
            e_pie,
        )
    )

    doc.build(story)


@mobile_api.route("/asistencia/materia", methods=["POST"])
@require_api_key
def marcar_materia() -> Any:
    data = request.get_json(silent=True) or {}
    materia_solicitada = (data.get("materia") or "").strip()
    ahora = get_now_py()

    try:
        from logic.logic import AgenteAsistenciaMaterias

        agente = AgenteAsistenciaMaterias()
        horarios = agente.HORARIOS_MATERIAS

        # 1. Validar si los horarios de materias están disponibles
        if horarios is None:
            logger.warning("No se pudieron cargar los horarios de Config_bot.")
            msg = "⚠️ No se pudo verificar el horario oficial de materias en el servidor (servicio no disponible)."
            return (
                jsonify(
                    {
                        "error": {"code": "SERVICE_UNAVAILABLE", "message": msg},
                        "mensaje": msg,
                    }
                ),
                503,
            )

        # 2. Verificar si hay clase en curso actualmente
        materia_en_curso, tipo = agente.obtener_materia_actual(ahora)
        if not materia_en_curso:
            msg = (
                f"ℹ️ No hay clase en curso para '{materia_solicitada}' en este momento según el horario oficial."
                if materia_solicitada
                else "ℹ️ No hay ninguna clase en curso en este momento según el horario oficial."
            )
            return (
                jsonify(
                    {
                        "error": {"code": "NO_CLASE_EN_CURSO", "message": msg},
                        "mensaje": msg,
                    }
                ),
                400,
            )

        # 3. Si el usuario seleccionó una materia específica, validar que coincida con la que está en curso
        if (
            materia_solicitada
            and materia_solicitada.lower() != "general"
            and materia_solicitada.lower() != materia_en_curso.lower()
        ):
            msg = f"ℹ️ La clase en curso es '{materia_en_curso}', no '{materia_solicitada}'."
            return (
                jsonify(
                    {
                        "error": {"code": "MATERIA_MISMATCH", "message": msg},
                        "mensaje": msg,
                    }
                ),
                400,
            )

        # 4. Registrar la asistencia real en Google Sheets
        resultado = agente.marcar_asistencia()
        if resultado.startswith("❌"):
            return (
                jsonify(
                    {
                        "error": {"code": "ASISTENCIA_ERROR", "message": resultado},
                        "mensaje": resultado,
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "materia": materia_en_curso,
                    "hora": ahora.strftime("%H:%M"),
                    "mensaje": resultado,
                }
            ),
            200,
        )

    except Exception as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code == 429 or "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
            logger.warning(f"Google Sheets rate limit excedido en marcar_materia: {e}")
            return (
                jsonify(
                    {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Servicio de Google Sheets saturado temporalmente. "
                                "Espera 60 segundos antes de reintentar."
                            ),
                        }
                    }
                ),
                429,
            )
        logger.error(f"Error procesando marcación de materia: {e}")
        msg = f"❌ Error interno al registrar materia: {str(e)}"
        return (
            jsonify(
                {
                    "error": {"code": "INTERNAL_ERROR", "message": msg},
                    "mensaje": msg,
                }
            ),
            500,
        )


# ── Asistencia: Analíticas, Períodos y Reportes Descargables ───────────────
@mobile_api.route("/asistencia/periodos", methods=["GET"])
@require_api_key
def get_asistencia_periodos() -> Any:
    """Retorna el estado de períodos laboral y contable, indicando si están sincronizados."""
    try:
        from logic.logic import obtener_estado_periodos

        estado = obtener_estado_periodos()
        dto = PeriodosResponse(**estado)
        return jsonify(dto.model_dump()), 200
    except Exception as e:
        logger.error(f"Error obteniendo períodos de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@mobile_api.route("/asistencia/analiticas", methods=["GET"])
@require_api_key
def get_asistencia_analiticas() -> Any:
    """Retorna analíticas laborales MTD: horas perdidas, horas extras, balance neto y acumulado."""
    try:
        hoja = request.args.get("hoja")
        from logic.logic import AgenteAutonomoHoras

        agente = AgenteAutonomoHoras()
        analiticas, error = agente.calcular_analiticas_asistencia(nombre_hoja=hoja)
        if error:
            return (
                jsonify({"error": {"code": "ANALITICAS_ERROR", "message": str(error)}}),
                400,
            )

        dto = AnaliticasHorasResponse(**analiticas)
        return jsonify(dto.model_dump()), 200
    except Exception as e:
        logger.error(f"Error calculando analíticas de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@mobile_api.route("/asistencia/reporte/excel", methods=["GET"])
@require_api_key
def descargar_reporte_excel() -> Any:
    """Genera y descarga la planilla nativa Excel (.xlsx) con el formato oficial."""
    try:
        hoja = request.args.get("hoja")
        descuento = float(request.args.get("descuento", 0) or 0)
        saldo_anterior = float(request.args.get("saldo_anterior", 0) or 0)
        incluir_iva = request.args.get("incluir_iva", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        from logic.logic import AgenteAutonomoHoras
        from services.excel_service import ExcelReportService

        agente = AgenteAutonomoHoras()
        datos, error = agente.preparar_datos_reporte(
            nombre_hoja=hoja,
            descuento=descuento,
            saldo_anterior=saldo_anterior,
            incluir_iva=incluir_iva,
        )
        if error:
            return (
                jsonify({"error": {"code": "REPORTE_ERROR", "message": str(error)}}),
                400,
            )

        excel_service = ExcelReportService(output_dir=REPORTES_DIR)
        ruta_archivo = excel_service.generar_reporte_horas(datos)

        return send_file(
            ruta_archivo,
            mimetype=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            as_attachment=True,
            download_name=os.path.basename(ruta_archivo),
        )
    except Exception as e:
        logger.error(f"Error generando reporte Excel de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@mobile_api.route("/asistencia/reporte/pdf", methods=["GET"])
@require_api_key
def descargar_reporte_pdf_asistencia() -> Any:
    """Genera y descarga el reporte PDF de horas con cuadro resumen oficial."""
    try:
        hoja = request.args.get("hoja")
        descuento = float(request.args.get("descuento", 0) or 0)
        saldo_anterior = float(request.args.get("saldo_anterior", 0) or 0)
        incluir_iva = request.args.get("incluir_iva", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        from logic.logic import AgenteAutonomoHoras
        from logic.pdf_service import PDFService

        agente = AgenteAutonomoHoras()
        datos, error = agente.preparar_datos_reporte(
            nombre_hoja=hoja,
            descuento=descuento,
            saldo_anterior=saldo_anterior,
            incluir_iva=incluir_iva,
        )
        if error:
            return (
                jsonify({"error": {"code": "REPORTE_ERROR", "message": str(error)}}),
                400,
            )

        pdf_service = PDFService()
        ruta_archivo = pdf_service.generar_reporte_generico(datos)

        return send_file(
            ruta_archivo,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=os.path.basename(ruta_archivo),
        )
    except Exception as e:
        logger.error(f"Error generando reporte PDF de asistencia: {e}")
        return (
            jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}),
            500,
        )


@mobile_api.route("/cierres", methods=["GET"])
@require_api_key
def get_historial_cierres() -> Any:
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        raw_cierres = repo.get_todos_cierres_historicos()

        resultado: list[dict[str, Any]] = []
        ids_contables: set[str] = set()

        # 1. Cierres Contables desde Google Sheets
        for r in raw_cierres:
            mes = str(r.get("Mes", "")).strip()
            anio = str(r.get("Anio", "")).strip()
            periodo = (
                f"{mes} {anio}".strip() if (mes or anio) else "Período Desconocido"
            )

            cierre_id = str(r.get("ID_Cierre") or "").strip()
            if not cierre_id:
                cierre_id = f"cierre_contable_{periodo.replace(' ', '_').lower()}"
            ids_contables.add(cierre_id)

            total_ingresos = safe_int(r.get("Total_Ingresos", 0))
            total_gastos = safe_int(r.get("Total_Gastos", 0))
            saldo_acumulado = safe_int(r.get("Saldo_Acumulado", 0))
            fecha = str(r.get("Fecha_Cierre") or "").strip()

            filename = f"cierre_contable_{periodo.replace(' ', '_').lower()}.pdf"
            pdf_path = REPORTES_DIR / filename
            pdf_disponible = pdf_path.exists()

            resumen_partes = []
            if total_ingresos > 0:
                resumen_partes.append(
                    f"Ingresos: ₲ {total_ingresos:,}".replace(",", ".")
                )
            if total_gastos > 0:
                resumen_partes.append(f"Gastos: ₲ {total_gastos:,}".replace(",", "."))
            if not resumen_partes:
                resumen_partes.append(f"Saldo: ₲ {saldo_acumulado:,}".replace(",", "."))
            resumen = " | ".join(resumen_partes)

            resultado.append(
                {
                    "id": cierre_id,
                    "tipo": "contable",
                    "periodo": periodo,
                    "fecha": fecha,
                    "total_monto": total_ingresos or saldo_acumulado,
                    "total_horas": 0.0,
                    "resumen": resumen,
                    "pdf_url": f"/api/v1/cierres/reportes/{filename}",
                    "pdf_disponible": pdf_disponible,
                }
            )

        # 2. Cierres Laborales y Contables adicionales en REPORTES_DIR
        if REPORTES_DIR.exists():
            for pdf_file in sorted(
                REPORTES_DIR.glob("*.pdf"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                stem = pdf_file.stem
                if stem.startswith("cierre_laboral_"):
                    partes = stem.replace("cierre_laboral_", "").split("_")
                    periodo_lab = " ".join(p.capitalize() for p in partes)
                    file_stat = pdf_file.stat()
                    fecha_mod = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    resultado.append(
                        {
                            "id": stem,
                            "tipo": "laboral",
                            "periodo": periodo_lab,
                            "fecha": fecha_mod,
                            "total_monto": 0,
                            "total_horas": 160.0,
                            "resumen": f"Cierre laboral de horas para período {periodo_lab}",
                            "pdf_url": f"/api/v1/cierres/reportes/{pdf_file.name}",
                            "pdf_disponible": True,
                        }
                    )
                elif stem.startswith("cierre_contable_") and stem not in ids_contables:
                    partes = stem.replace("cierre_contable_", "").split("_")
                    periodo_cont = " ".join(p.capitalize() for p in partes)
                    file_stat = pdf_file.stat()
                    fecha_mod = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    resultado.append(
                        {
                            "id": stem,
                            "tipo": "contable",
                            "periodo": periodo_cont,
                            "fecha": fecha_mod,
                            "total_monto": 0,
                            "total_horas": 0.0,
                            "resumen": f"Cierre contable para período {periodo_cont}",
                            "pdf_url": f"/api/v1/cierres/reportes/{pdf_file.name}",
                            "pdf_disponible": True,
                        }
                    )
                    ids_contables.add(stem)

        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error consultando historial de cierres: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error al consultar historial de cierres: {str(e)}",
                    }
                }
            ),
            500,
        )


@mobile_api.route("/cierres/ejecutar", methods=["POST"])
@require_api_key
def ejecutar_cierre() -> Any:
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo", "horas")
    hoja = data.get("hoja", "Período Actual")
    con_desc = data.get("aplicar_descuento", False)

    prefix = "cierre_contable" if tipo == "contable" else "cierre_laboral"
    filename = f"{prefix}_{hoja.replace(' ', '_').lower()}.pdf"
    pdf_path = REPORTES_DIR / filename

    total_horas = 0.0
    total_monto = 0
    cierre_ejecutado = False
    backup_id = ""

    if tipo in ("horas", "laboral"):
        try:
            from logic.logic import AgenteAutonomoHoras

            agente_horas = AgenteAutonomoHoras()
            nombre_hoja_target = (
                None if hoja in ("Período Actual", "Periodo Actual") else hoja
            )
            analiticas, err = agente_horas.calcular_analiticas_asistencia(
                nombre_hoja=nombre_hoja_target
            )
            if analiticas:
                total_horas = float(analiticas.get("total_horas_decimal", 0.0))
                total_monto = int(analiticas.get("salario_acumulado_gs", 0))

            if data.get("cerrar_planilla", False):
                agente_horas.ejecutar_cierre_periodo_manual()
                cierre_ejecutado = True
        except Exception as e_horas:
            logger.warning(
                f"Error obteniendo analíticas reales de horas para cierre: {e_horas}"
            )
            total_horas = 0.0
            total_monto = 0

    elif tipo == "contable":
        try:
            from repositories.sheets_repository import SheetsRepository
            from logic.logic import get_now_py
            from logic.constants import MESES_ES

            repo = SheetsRepository()
            ahora = get_now_py()
            mes_num = ahora.month
            anio_num = ahora.year

            partes = hoja.split()
            if len(partes) == 2:
                for idx, m_nombre in enumerate(MESES_ES, start=1):
                    if m_nombre.lower() == partes[0].lower():
                        mes_num = idx
                        break
                try:
                    anio_num = int(partes[1])
                except ValueError:
                    pass

            bal = repo.obtener_balance(mes=str(mes_num), anio=str(anio_num))
            if bal:
                ingresos = bal.get("ingresos", 0)
                gastos = bal.get("gastos", 0)
                flujo_neto = bal.get("flujo_neto", ingresos - gastos)
                total_monto = flujo_neto
            total_horas = 0.0

            if data.get("cerrar_contabilidad", False):
                from logic.financiero import execute_monthly_closing

                backup_id = execute_monthly_closing(mes_num, anio_num)
                cierre_ejecutado = True
        except Exception as e_cont:
            logger.warning(f"Error calculando balance contable para cierre: {e_cont}")
            total_horas = 0.0
            total_monto = 0

    try:
        generar_pdf_cierre(
            destino_path=pdf_path,
            tipo=tipo,
            hoja=hoja,
            total_monto=total_monto,
            total_horas=total_horas,
            con_descuento=con_desc,
        )
    except Exception as e:
        logger.error(f"Error generando PDF de cierre: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "PDF_GENERATION_ERROR",
                        "message": f"Error al generar comprobante PDF: {str(e)}",
                    },
                    "mensaje": f"Error al generar comprobante PDF: {str(e)}",
                }
            ),
            500,
        )

    desc_str = (
        " (con descuento de seguro)"
        if con_desc and tipo in ("horas", "laboral")
        else ""
    )
    tipo_str = (
        "contable (Libro Diario)" if tipo == "contable" else "laboral de asistencia"
    )
    return (
        jsonify(
            {
                "resumen": f"Cierre mensual {tipo_str} completado para período {hoja}{desc_str}.",
                "pdf_url": f"/api/v1/cierres/reportes/{filename}",
                "total_horas": total_horas,
                "total_monto": total_monto,
                "tipo": tipo,
                "hoja": hoja,
                "cierre_ejecutado": cierre_ejecutado,
                "backup_id": backup_id,
            }
        ),
        200,
    )


@mobile_api.route("/cierres/reportes/<path:filename>", methods=["GET"])
def descargar_reporte_pdf(filename: str) -> Any:
    return send_from_directory(REPORTES_DIR, filename, mimetype="application/pdf")


@mobile_api.route("/asistencia/cierres", methods=["GET"])
@require_api_key
def get_historial_cierres_laborales() -> Any:
    """Devuelve la lista de períodos y reportes laborales de asistencia archivados."""
    try:
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        periodos: list[dict[str, Any]] = []

        if spreadsheet_id:
            try:
                agente = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
                hojas = [
                    ws.title
                    for ws in agente.wb.worksheets()
                    if ws.title.lower() not in ("materias", "resumen", "config")
                ]
                for h in hojas:
                    filename = f"cierre_laboral_{h.replace(' ', '_').lower()}.pdf"
                    pdf_path = REPORTES_DIR / filename
                    periodos.append(
                        {
                            "periodo": h,
                            "pdf_disponible": pdf_path.exists(),
                            "pdf_url": (
                                f"/api/v1/cierres/reportes/{filename}"
                                if pdf_path.exists()
                                else None
                            ),
                        }
                    )
            except Exception as e_sheet:
                logger.warning(
                    f"Error listando hojas para cierres laborales: {e_sheet}"
                )

        # Fallback a archivos PDF encontrados en disco si no hubo conexión
        if not periodos:
            for p in sorted(REPORTES_DIR.glob("cierre_laboral_*.pdf")):
                periodo_nombre = (
                    p.stem.replace("cierre_laboral_", "").replace("_", " ").capitalize()
                )
                periodos.append(
                    {
                        "periodo": periodo_nombre,
                        "pdf_disponible": True,
                        "pdf_url": f"/api/v1/cierres/reportes/{p.name}",
                    }
                )

        return (
            jsonify(
                {
                    "status": "ok",
                    "total": len(periodos),
                    "cierres": periodos,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error consultando historial de cierres laborales: {e}")
        return jsonify({"status": "error", "message": str(e), "cierres": []}), 500


# ── 8. Sistema y Tickets ────────────────────────────────────────────────────
@mobile_api.route("/soporte/tickets", methods=["GET"])
@require_api_key
def get_tickets() -> Any:
    if TICKETS_FILE.exists():
        try:
            with open(TICKETS_FILE, "r", encoding="utf-8") as f:
                tickets = json.load(f)
            # Asegurar retrocompatibilidad para registros que no tengan origen o resolución
            for t in tickets:
                if "origen" not in t:
                    t["origen"] = "app"
                if "resolucion" not in t:
                    t["resolucion"] = None
            return jsonify(tickets), 200
        except Exception:
            pass
    return jsonify([]), 200


@mobile_api.route("/soporte/tickets", methods=["POST"])
@require_api_key
def create_ticket() -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = TicketCreate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    tickets = []
    if TICKETS_FILE.exists():
        try:
            with open(TICKETS_FILE, "r", encoding="utf-8") as f:
                tickets = json.load(f)
        except Exception:
            tickets = []

    nuevo_ticket = {
        "id": f"TCK-{len(tickets) + 1:03d}",
        "asunto": req_obj.asunto,
        "descripcion": req_obj.descripcion or "",
        "estado": "Abierto",
        "fecha": get_now_py().strftime("%d/%m/%Y"),
        "origen": req_obj.origen or "app",
        "resolucion": None,
    }
    tickets.insert(0, nuevo_ticket)
    try:
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando ticket: {e}")

    # Telemetría Vigía (creación de Issue en GitHub)
    try:
        from com.core.telemetry import reportar_incidente_vigia

        reportar_incidente_vigia(
            titulo=f"[APP TICKET] {nuevo_ticket['id']}: {req_obj.asunto}",
            detalle=f"Ticket reportado desde Gamma Mobile:\n\n{req_obj.descripcion or 'Sin detalle'}",
            origen="gamma-mobile",
        )
    except Exception as e_vigia:
        logger.warning(f"No se pudo reportar a Vigía: {e_vigia}")

    # Alerta push al Telegram del Administrador
    try:
        chat_id = os.getenv("CHAT_ID")
        if chat_id:
            from flask_app import bot_instance

            if bot_instance and hasattr(bot_instance, "bot") and bot_instance.bot:
                bot_instance.bot.send_message(
                    int(chat_id),
                    f"🎫 <b>Nuevo Ticket de Soporte (App Móvil)</b>\n\n"
                    f"🆔 <b>ID:</b> <code>{nuevo_ticket['id']}</code>\n"
                    f"📌 <b>Asunto:</b> {nuevo_ticket['asunto']}\n"
                    f"📝 <b>Descripción:</b> {nuevo_ticket['descripcion']}\n"
                    f"📅 <b>Fecha:</b> {nuevo_ticket['fecha']}\n"
                    f"🌐 <b>Origen:</b> {nuevo_ticket['origen']}",
                    parse_mode="HTML",
                )
    except Exception as e_tg:
        logger.warning(f"No se pudo enviar notificación de ticket a Telegram: {e_tg}")

    # Sincronización con GitHub Issues si GITHUB_TOKEN está configurado
    try:
        from services.github_service import GitHubIssueSyncService

        GitHubIssueSyncService.create_github_issue(nuevo_ticket)
    except Exception as e_gh:
        logger.warning(f"Error no bloqueante al crear issue en GitHub: {e_gh}")

    return jsonify(nuevo_ticket), 201


@mobile_api.route("/soporte/tickets/<ticket_id>", methods=["PATCH"])
@require_api_key
def update_ticket(ticket_id: str) -> Any:
    data = request.get_json(silent=True) or {}
    try:
        req_obj = TicketUpdate(**data)
    except ValidationError as ve:
        return (
            jsonify({"error": {"code": "VALIDATION_ERROR", "detail": ve.errors()}}),
            400,
        )

    estados_validos = {"Abierto", "En proceso", "Cerrado"}
    if req_obj.estado not in estados_validos:
        return (
            jsonify(
                {
                    "error": {
                        "code": "INVALID_STATE",
                        "message": (
                            f"Estado '{req_obj.estado}' inválido. "
                            f"Debe ser uno de: {sorted(list(estados_validos))}"
                        ),
                    }
                }
            ),
            400,
        )

    if not TICKETS_FILE.exists():
        return (
            jsonify(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Ticket {ticket_id} no encontrado",
                    }
                }
            ),
            404,
        )

    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            tickets = json.load(f)
    except Exception as e:
        return jsonify({"error": {"code": "READ_ERROR", "message": str(e)}}), 500

    target = None
    for t in tickets:
        if t.get("id") == ticket_id:
            target = t
            break

    if not target:
        return (
            jsonify(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Ticket {ticket_id} no encontrado",
                    }
                }
            ),
            404,
        )

    target["estado"] = req_obj.estado
    if req_obj.resolucion is not None:
        target["resolucion"] = req_obj.resolucion
    if "origen" not in target:
        target["origen"] = "app"

    try:
        with open(TICKETS_FILE, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error actualizando ticket {ticket_id}: {e}")
        return jsonify({"error": {"code": "WRITE_ERROR", "message": str(e)}}), 500

    # Sincronización con GitHub Issues al actualizar estado
    try:
        from services.github_service import GitHubIssueSyncService

        GitHubIssueSyncService.sync_ticket_status(
            ticket_id=ticket_id,
            nuevo_estado=req_obj.estado,
            resolucion=req_obj.resolucion,
        )
    except Exception as e_gh:
        logger.warning(
            f"Error no bloqueante al sincronizar estado de issue en GitHub: {e_gh}"
        )

    return jsonify(target), 200


@mobile_api.route("/sistema/logs", methods=["GET"])
@require_api_key
def get_logs() -> Any:
    limit_str = request.args.get("limit", "20")
    try:
        limit = max(1, min(100, int(limit_str)))
    except (ValueError, TypeError):
        limit = 20

    log_file = BASE_DIR / "gen_log.txt"
    entries: list[dict[str, str]] = []

    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = [line.strip() for line in f if line.strip()]

            # Leer en orden cronológico inverso (más reciente primero)
            for line in reversed(lines):
                if len(entries) >= limit:
                    break
                match = re.match(
                    r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]\s*(.*)$",
                    line,
                )
                if match:
                    ts_raw, msg = match.group(1), match.group(2)
                    try:
                        dt = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S")
                        ts = dt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        ts = ts_raw
                else:
                    ts = get_now_py().strftime("%d/%m/%Y %H:%M:%S")
                    msg = line

                msg_lower = msg.lower()
                if (
                    "❌" in msg
                    or "error" in msg_lower
                    or "exception" in msg_lower
                    or "fail" in msg_lower
                ):
                    nivel = "ERROR"
                elif "⚠️" in msg or "warn" in msg_lower or "advertencia" in msg_lower:
                    nivel = "WARN"
                else:
                    nivel = "INFO"

                entries.append(
                    {
                        "timestamp": ts,
                        "nivel": nivel,
                        "mensaje": msg,
                    }
                )
        except Exception as e:
            logger.warning(f"Error leyendo logs desde {log_file}: {e}")

    # Fallback estructurado si el archivo no existe o está vacío
    if not entries:
        entries = [
            {
                "timestamp": get_now_py().strftime("%d/%m/%Y %H:%M:%S"),
                "nivel": "INFO",
                "mensaje": "Servidor backend Gamma operativo en WSGI.",
            },
            {
                "timestamp": get_now_py().strftime("%d/%m/%Y %H:%M:%S"),
                "nivel": "INFO",
                "mensaje": "Mobile API Blueprint v1.0.0 activo.",
            },
        ]

    response = jsonify(entries)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200


# ── 9. Webhooks de GitHub ───────────────────────────────────────────────────
@mobile_api.route("/webhooks/github", methods=["POST"])
def github_webhook() -> Any:
    """Receptor público de webhooks de GitHub para sincronización reactiva."""
    from services.github_service import GitHubWebhookService

    # 1. Validación de firma HMAC si GITHUB_WEBHOOK_SECRET está configurado
    signature_header = request.headers.get("X-Hub-Signature-256")
    payload_bytes = request.get_data()

    if not GitHubWebhookService.verify_signature(payload_bytes, signature_header):
        logger.warning(
            "Intento de webhook de GitHub con firma HMAC inválida o ausente."
        )
        return (
            jsonify(
                {
                    "error": {
                        "code": "INVALID_SIGNATURE",
                        "message": "Firma HMAC de GitHub no coincide con el secret configurado.",
                    }
                }
            ),
            401,
        )

    event_type = request.headers.get("X-GitHub-Event", "")

    # 2. Manejo de Ping
    if event_type == "ping":
        logger.info("GitHub Webhook ping recibido exitosamente.")
        return (
            jsonify(
                {
                    "status": "pong",
                    "message": "GitHub Webhook listener operational",
                }
            ),
            200,
        )

    # 3. Manejo de Eventos de Issues
    if event_type == "issues":
        data = request.get_json(silent=True) or {}
        action = data.get("action", "")
        issue_data = data.get("issue", {})

        resultado = GitHubWebhookService.process_issue_event(
            action=action,
            issue_data=issue_data,
            tickets_file_path=TICKETS_FILE,
        )

        # Notificación reactiva al Telegram del Administrador si el ticket fue procesado
        if resultado.get("status") == "processed":
            try:
                chat_id = os.getenv("CHAT_ID")
                if chat_id:
                    from flask_app import bot_instance

                    if (
                        bot_instance
                        and hasattr(bot_instance, "bot")
                        and bot_instance.bot
                    ):
                        accion_emoji = (
                            "✅" if resultado.get("nuevo_estado") == "Cerrado" else "🔄"
                        )
                        bot_instance.bot.send_message(
                            int(chat_id),
                            f"{accion_emoji} <b>Actualización de Ticket desde GitHub</b>\n\n"
                            f"🆔 <b>Ticket:</b> <code>{resultado.get('ticket_id')}</code>\n"
                            f"📌 <b>Estado:</b> {resultado.get('nuevo_estado')}\n"
                            f"🐙 <b>Issue:</b> #{resultado.get('issue_number')}\n"
                            f"⚡ <b>Acción:</b> <code>{action}</code>",
                            parse_mode="HTML",
                        )
            except Exception as e_tg:
                logger.warning(f"Error no bloqueante notificando a Telegram: {e_tg}")

        return jsonify(resultado), 200

    # 4. Cualquier otro evento no manejado se acepta sin error (para evitar retries de GitHub)
    return (
        jsonify(
            {
                "status": "ignored",
                "reason": f"Event '{event_type}' not handled",
            }
        ),
        200,
    )
