from __future__ import annotations

import time
from typing import Any

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import MovimientoCreate, ParseMovementRequest, ParsedMovement
from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py, safe_int
from src.utils.nlp_parser import FinanceNLParser

logger = setup_logger("routes_movimientos")

movimientos_bp = Blueprint("movimientos_v1", __name__)


def _get_processed_clients_store() -> dict[str, float]:
    try:
        from api.blueprint import _PROCESSED_CLIENT_IDS

        return _PROCESSED_CLIENT_IDS
    except Exception:
        # Fallback local si blueprint aún se está inicializando
        global _LOCAL_PROCESSED_CLIENT_IDS
        return _LOCAL_PROCESSED_CLIENT_IDS


_LOCAL_PROCESSED_CLIENT_IDS: dict[str, float] = {}


@movimientos_bp.route("/movimientos", methods=["GET"])
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


@movimientos_bp.route("/movimientos", methods=["POST"])
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
    processed_clients = _get_processed_clients_store()
    if client_id:
        if client_id in processed_clients:
            if now_ts - processed_clients[client_id] < 86400:  # 24 horas
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
        processed_clients[client_id] = now_ts

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

    # Evaluación preventiva de techo presupuestario si es un Gasto
    alerta_presupuesto = None
    if req_obj.movimiento.value.lower() == "gasto":
        try:
            from logic.financiero import evaluar_techo_presupuestario

            alerta = evaluar_techo_presupuestario(
                categoria=req_obj.categoria,
                monto_nuevo=float(total),
            )
            if alerta.get("alerta_emitida"):
                alerta_presupuesto = alerta
        except Exception as e_alerta:
            logger.debug(f"Error evaluando alerta de presupuesto: {e_alerta}")

    payload_resp: dict[str, Any] = {
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
    if alerta_presupuesto:
        payload_resp["alerta_presupuesto"] = alerta_presupuesto

    response = jsonify(payload_resp)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response, 200


@movimientos_bp.route("/movimientos/ocr", methods=["POST"])
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


@movimientos_bp.route("/movimientos/parse", methods=["POST"])
@require_api_key
def parse_movimiento() -> Any:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return (
            jsonify(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Payload JSON requerido con la clave 'texto'",
                    }
                }
            ),
            422,
        )

    try:
        req = ParseMovementRequest(**body)
    except ValidationError as ve:
        return (
            jsonify(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Texto inválido o no proporcionado para el parser",
                        "detail": ve.errors(),
                    }
                }
            ),
            422,
        )

    result = FinanceNLParser.parse(req.texto)
    parsed_resp = ParsedMovement(**result.to_dict())
    return jsonify(parsed_resp.model_dump()), 200
