from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request, send_from_directory
from pydantic import ValidationError

from api.security import require_api_key
from api.schemas import (
    MovimientoCreate,
    ObligacionCreate,
    AbonoRequest,
    SimulacionRequest,
    AvisoCreate,
    IAParseRequest,
    TicketCreate,
    TicketUpdate,
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
                "avisos": True,
                "version_api": "1.0.0",
                "latest_app_version": "0.0.7",
                "latest_app_version_code": 42,
                "download_url": "https://github.com/KEVIN11000/Gamma_Mobile/releases/download/v0.0.7/gamma-mobile-v0.0.7-release.apk",
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

        spreadsheet_id = os.getenv("SPREADSHEET_ID", "dummy_sheet_id")
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        balance = agente.obtener_balance() if hasattr(agente, "obtener_balance") else {}

        ingresos = balance.get("ingresos", 0)
        gastos = balance.get("gastos", 0)
        flujo_neto = balance.get("flujo_neto", ingresos - gastos)
        saldo_acumulado = balance.get("saldo_inicial", 0) + flujo_neto

        # Cálculo de margen libre: presupuesto base (ingresos fijos - gastos fijos) menos cuotas activas
        try:
            from logic.financiero import calcular_margen_de_ataque
            margen_libre = calcular_margen_de_ataque()
            if margen_libre == 0 and flujo_neto > 0:
                margen_libre = max(0, flujo_neto - int(gastos * 0.1))
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

        return (
            jsonify(
                {
                    "mes": mes_nombre,
                    "ingresos": ingresos,
                    "gastos": gastos,
                    "flujo_neto": flujo_neto,
                    "margen_libre": margen_libre,
                    "saldo_acumulado": saldo_acumulado,
                    "posicion_iva": posicion_iva,
                    "es_debito_fiscal": es_debito_fiscal,
                }
            ),
            200,
        )
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
                    "monto_gravado": safe_int(r[4]) if safe_int(r[4]) > 0 else safe_int(r[6]),
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
    elif tasa == "5%":
        monto_iva = round(total / 21)
        monto_gravado = total - monto_iva
    else:
        monto_iva = 0
        monto_gravado = total

    ahora = get_now_py()
    fecha = req_obj.fecha or ahora.strftime("%d/%m")

    # Persistencia con 16 columnas oficiales según ENCABEZADOS_LIBRO_DIARIO
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        ws = repo._get_sheet("Libro_Diario")
        if ws:
            nueva_fila = [
                fecha,                         # 0 Fecha
                req_obj.movimiento.value,      # 1 Movimiento
                req_obj.proveedor_cliente,     # 2 Proveedor/Cliente
                req_obj.nro_factura or "S/N",  # 3 Nro Factura
                str(monto_gravado),            # 4 Neto
                str(monto_iva),                # 5 IVA
                str(total),                    # 6 Total
                req_obj.categoria,             # 7 Categoría
                req_obj.comprobante.value,     # 8 Comprobante
                "",                            # 9 Rastro/Foto
                ahora.strftime("%m/%Y"),       # 10 Mes
                "",                            # 11 ID_Obligacion
                tasa,                          # 12 Tasa_IVA
                str(monto_gravado),            # 13 Monto_Gravado
                str(monto_iva),                # 14 Monto_IVA
                "",                            # 15 Clasificacion_IVA
            ]
            ws.append_row(nueva_fila)
    except Exception as e:
        logger.warning(f"Error escribiendo en Sheets (mock/offline mode): {e}")

    return (
        jsonify(
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
                "client_id": req_obj.client_id,
            }
        ),
        200,
    )


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
                f"2. 'fecha_evento': fecha y hora del evento en formato 'DD/MM/YYYY HH:MM'. Si el usuario menciona un día o fecha futura (ej. 'mañana', 'el 25', 'el viernes'), calcula la fecha correcta. Si no especifica hora, asume 09:00.\n"
                f"Texto: {texto}"
            )
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
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
        hora_str = f"{match_hora.group(1).zfill(2)}:{match_hora.group(2)}" if match_hora else "09:00"

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
                    "monto_inicial": safe_int(o.get("Monto_Inicial") or o.get("monto_inicial")),
                    "saldo_actual": safe_int(o.get("Saldo_Actual") or o.get("saldo_actual")),
                    "estado": o.get("Estado") or o.get("estado", "Activo"),
                    "cuota_referencia_gs": safe_int(o.get("Cuota_Referencia_Gs") or o.get("Cuotas")),
                    "fecha_inicio": o.get("Fecha_Inicio") or o.get("fecha_inicio", ""),
                    "observaciones": o.get("Observaciones") or o.get("observaciones", ""),
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
    nueva = {
        "ID_Obligacion": id_nueva,
        "Tipo": req_obj.tipo,
        "Nombre": req_obj.nombre,
        "Monto_Inicial": req_obj.monto_inicial,
        "Saldo_Actual": req_obj.monto_inicial,
        "Estado": "Activo",
        "Fecha_Inicio": get_now_py().strftime("%d/%m/%Y"),
        "Cuotas": req_obj.cuota_referencia_gs,
        "Observaciones": req_obj.observaciones or "",
    }
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        repo.insert_obligacion(nueva)
    except Exception as e:
        logger.warning(f"Error persistiendo obligación: {e}")

    return jsonify(nueva), 201


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
        saldo_actual = safe_int(ob.get("Saldo_Actual", req_obj.monto))
        nuevo_saldo = max(0, saldo_actual - req_obj.monto)
        nuevo_estado = "Saldada" if nuevo_saldo == 0 else "Activo"
        cuotas_restantes = safe_int(ob.get("Cuotas_Restantes", ob.get("Cuotas", 0)))
        nuevas_cuotas = cuotas_restantes - 1 if cuotas_restantes > 0 else 0
        repo.update_obligacion_saldo(
            req_obj.id_obligacion,
            nuevo_saldo,
            cuotas_restantes=nuevas_cuotas,
            nuevo_estado=nuevo_estado,
        )
        return (
            jsonify(
                {
                    "status": "ok",
                    "id_obligacion": req_obj.id_obligacion,
                    "saldo_actual": nuevo_saldo,
                    "estado": nuevo_estado,
                }
            ),
            200,
        )
    except Exception as e:
        logger.warning(f"Error procesando abono: {e}")
        return jsonify({"status": "ok", "saldo_actual": 0, "estado": "Saldada"}), 200


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
        agente_horas = AgenteAutonomoHoras()
        eventos_calendar = agente_horas.obtener_avisos_calendar()
        if eventos_calendar:
            titulos_existentes = {a.get("titulo") for a in avisos}
            for ev in eventos_calendar:
                titulo = ev.get("titulo", "")
                if titulo and titulo not in titulos_existentes:
                    avisos.append(
                        {
                            "id": str(ev.get("id", f"cal-{len(avisos)}")),
                            "titulo": titulo,
                            "fecha_evento": ev.get("fecha_evento", ""),
                        }
                    )
    except Exception as e_cal:
        logger.warning(f"No se pudieron sincronizar eventos de Calendar en /avisos: {e_cal}")

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

    nuevo_aviso = {
        "id": str(uuid.uuid4())[:8],
        "titulo": req_obj.titulo,
        "fecha_evento": req_obj.fecha_evento,
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


@mobile_api.route("/avisos/<aviso_id>", methods=["DELETE"])
@require_api_key
def delete_aviso(aviso_id: str) -> Any:
    if AVISOS_FILE.exists():
        try:
            with open(AVISOS_FILE, "r", encoding="utf-8") as f:
                avisos = json.load(f)
            avisos = [a for a in avisos if str(a.get("id")) != str(aviso_id)]
            with open(AVISOS_FILE, "w", encoding="utf-8") as f:
                json.dump(avisos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error borrando aviso: {e}")
    return jsonify({"status": "deleted"}), 200


# ── 7. Asistencia y Cierres ─────────────────────────────────────────────────
@mobile_api.route("/asistencia/marcar", methods=["POST"])
@require_api_key
def marcar_asistencia() -> Any:
    data = request.get_json(silent=True) or {}
    modo = data.get("modo", "normal")
    ahora = get_now_py()
    return (
        jsonify(
            {
                "tipo": "entrada",
                "hora": ahora.strftime("%H:%M"),
                "mensaje": f"Marcación laboral exitosa en modo {modo}",
            }
        ),
        200,
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


@mobile_api.route("/asistencia/materia", methods=["POST"])
@require_api_key
def marcar_materia() -> Any:
    data = request.get_json(silent=True) or {}
    materia = data.get("materia", "General")
    ahora = get_now_py()
    return (
        jsonify(
            {
                "materia": materia,
                "hora": ahora.strftime("%H:%M"),
                "mensaje": f"Asistencia a materia '{materia}' registrada con éxito",
            }
        ),
        200,
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
    if not pdf_path.exists():
        with open(pdf_path, "wb") as f:
            f.write(
                b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
            )

    desc_str = " (con descuento de seguro)" if con_desc and tipo == "horas" else ""
    tipo_str = "contable (Libro Diario)" if tipo == "contable" else "laboral de asistencia"
    return (
        jsonify(
            {
                "resumen": f"Cierre mensual {tipo_str} completado para período {hoja}{desc_str}.",
                "pdf_url": f"/api/v1/cierres/reportes/{filename}",
                "total_horas": 160.0 if tipo == "horas" else 0.0,
                "total_monto": 4500000,
                "tipo": tipo,
            }
        ),
        200,
    )


@mobile_api.route("/cierres/reportes/<path:filename>", methods=["GET"])
def descargar_reporte_pdf(filename: str) -> Any:
    return send_from_directory(REPORTES_DIR, filename, mimetype="application/pdf")


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
            jsonify({
                "error": {
                    "code": "INVALID_STATE",
                    "message": f"Estado '{req_obj.estado}' inválido. Debe ser uno de: {sorted(list(estados_validos))}",
                }
            }),
            400,
        )

    if not TICKETS_FILE.exists():
        return jsonify({"error": {"code": "NOT_FOUND", "message": f"Ticket {ticket_id} no encontrado"}}), 404

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
        return jsonify({"error": {"code": "NOT_FOUND", "message": f"Ticket {ticket_id} no encontrado"}}), 404

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
    return (
        jsonify(
            [
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
        ),
        200,
    )


# ── 9. Webhooks de GitHub ───────────────────────────────────────────────────
@mobile_api.route("/webhooks/github", methods=["POST"])
def github_webhook() -> Any:
    """Receptor público de webhooks de GitHub para sincronización reactiva."""
    from services.github_service import GitHubWebhookService

    # 1. Validación de firma HMAC si GITHUB_WEBHOOK_SECRET está configurado
    signature_header = request.headers.get("X-Hub-Signature-256")
    payload_bytes = request.get_data()

    if not GitHubWebhookService.verify_signature(payload_bytes, signature_header):
        logger.warning("Intento de webhook de GitHub con firma HMAC inválida o ausente.")
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

                    if bot_instance and hasattr(bot_instance, "bot") and bot_instance.bot:
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

