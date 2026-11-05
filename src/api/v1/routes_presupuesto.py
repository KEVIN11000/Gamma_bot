from __future__ import annotations

from typing import Any
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from api.schemas import (
    GastoFijoItem,
    PresupuestoFijosResponse,
    GastoFijoUpdate,
    GastoFijoCreate,
    SalarioBaseUpdate,
    TechoPresupuestarioItem,
)
from api.security import require_api_key
from logger_config import setup_logger

logger = setup_logger("routes_presupuesto")

presupuesto_bp = Blueprint("presupuesto_v1", __name__)


@presupuesto_bp.route("/presupuesto/fijos", methods=["GET"])
@require_api_key
def get_gastos_fijos() -> Any:
    """Retorna el salario base y el desglose de gastos fijos por categoría."""
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        salario_base, total_gf_base = repo.obtener_presupuesto_base_completo()
        gf_data = repo.obtener_gastos_fijos()

        gastos_map = gf_data.get("gastos", {})
        total_acumulado = gf_data.get("total", total_gf_base)

        categorias: dict[str, list[dict[str, Any]]] = {}
        for cat, items in gastos_map.items():
            categorias[cat] = [
                GastoFijoItem(
                    concepto=str(item.get("concepto", "")).strip(),
                    monto=int(item.get("monto", 0)),
                    concepto_id=str(item.get("concepto", "")).strip(),
                ).model_dump()
                for item in items
                if str(item.get("concepto", "")).strip()
            ]

        resp = PresupuestoFijosResponse(
            salario_base=int(salario_base),
            total_gastos_fijos=int(total_acumulado),
            categorias=categorias,  # type: ignore[arg-type]
        )
        return jsonify(resp.model_dump()), 200
    except Exception as exc:
        logger.error(f"Error consultando gastos fijos: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "SHEETS_ERROR",
                    "mensaje": f"No se pudo consultar Presupuesto_Base: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )


@presupuesto_bp.route("/presupuesto/fijos/<concepto>", methods=["PUT"])
@require_api_key
def update_gasto_fijo(concepto: str) -> Any:
    """Actualiza el monto mensual de un gasto fijo existente."""
    payload = request.get_json(silent=True) or {}
    try:
        req = GastoFijoUpdate(**payload)
    except ValidationError as ve:
        return (
            jsonify(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "mensaje": "Datos de actualización inválidos.",
                    "detalles": ve.errors(),
                }
            ),
            400,
        )

    concepto_limpio = concepto.strip()
    if not concepto_limpio:
        return (
            jsonify(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "mensaje": "El concepto no puede estar vacío.",
                    "detalles": None,
                }
            ),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        actualizado = repo.actualizar_monto_gasto_fijo(
            concepto_id=concepto_limpio, nuevo_monto=req.nuevo_monto
        )

        if not actualizado:
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "NOT_FOUND",
                        "mensaje": f"No se encontró el concepto fijo '{concepto_limpio}'.",
                        "detalles": None,
                    }
                ),
                404,
            )

        return (
            jsonify(
                {
                    "status": "ok",
                    "concepto": concepto_limpio,
                    "nuevo_monto": req.nuevo_monto,
                    "mensaje": "Monto de gasto fijo actualizado correctamente.",
                }
            ),
            200,
        )
    except Exception as exc:
        logger.error(
            f"Error actualizando gasto fijo '{concepto_limpio}': {exc}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": True,
                    "code": "SHEETS_ERROR",
                    "mensaje": f"Error al actualizar en Google Sheets: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )


@presupuesto_bp.route("/presupuesto/fijos", methods=["POST"])
@require_api_key
def add_gasto_fijo() -> Any:
    """Da de alta un nuevo concepto de gasto fijo en Presupuesto_Base."""
    payload = request.get_json(silent=True) or {}
    try:
        req = GastoFijoCreate(**payload)
    except ValidationError as ve:
        return (
            jsonify(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "mensaje": "Datos de creación de gasto fijo inválidos.",
                    "detalles": ve.errors(),
                }
            ),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        creado = repo.agregar_gasto_fijo(
            categoria=req.categoria.strip(),
            concepto=req.concepto.strip(),
            monto=req.monto,
        )

        if not creado:
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "INSERTION_ERROR",
                        "mensaje": "No se pudo registrar la fila en Presupuesto_Base.",
                        "detalles": None,
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "status": "ok",
                    "concepto": req.concepto.strip(),
                    "categoria": req.categoria.strip(),
                    "monto": req.monto,
                    "mensaje": "Gasto fijo registrado con éxito en Presupuesto_Base.",
                }
            ),
            201,
        )
    except Exception as exc:
        logger.error(f"Error agregando gasto fijo: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "SHEETS_ERROR",
                    "mensaje": f"Error al insertar en Google Sheets: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )


@presupuesto_bp.route("/presupuesto/salario-base", methods=["PUT"])
@require_api_key
def update_salario_base() -> Any:
    """Actualiza o crea el salario base en Presupuesto_Base."""
    payload = request.get_json(silent=True) or {}
    try:
        req = SalarioBaseUpdate(**payload)
    except ValidationError as ve:
        return (
            jsonify(
                {
                    "error": True,
                    "code": "VALIDATION_ERROR",
                    "mensaje": "Monto de salario inválido.",
                    "detalles": ve.errors(),
                }
            ),
            400,
        )

    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        actualizado = repo.upsert_salario_presupuesto_base(
            nuevo_salario=req.nuevo_salario
        )

        if not actualizado:
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "UPDATE_ERROR",
                        "mensaje": "No se pudo actualizar el salario base.",
                        "detalles": None,
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "status": "ok",
                    "nuevo_salario": req.nuevo_salario,
                    "mensaje": "Salario base actualizado en el presupuesto.",
                }
            ),
            200,
        )
    except Exception as exc:
        logger.error(f"Error actualizando salario base: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "SHEETS_ERROR",
                    "mensaje": f"Error al actualizar salario en Google Sheets: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )


@presupuesto_bp.route("/presupuesto/techos", methods=["GET"])
@require_api_key
def get_techos_presupuestarios() -> Any:
    """Retorna el estado de consumo y alertas de todas las categorías con techo asignado."""
    try:
        from repositories.sheets_repository import SheetsRepository
        from repositories.local_repository import get_local_repository
        from logic.financiero import evaluar_techo_presupuestario
        from logic.constants import ENCABEZADOS_PRESUPUESTO_BASE

        sheets_repo = SheetsRepository()
        local_repo = get_local_repository()

        categorias_a_evaluar: set[str] = set()

        # 1. Extraer categorías desde Presupuesto_Base
        ws_pb = sheets_repo._get_sheet("Presupuesto_Base")
        if ws_pb:
            records = sheets_repo._get_records(ws_pb, ENCABEZADOS_PRESUPUESTO_BASE)
            for r in records:
                cat = str(r.get("Categoria", "")).strip()
                if cat:
                    categorias_a_evaluar.add(cat)

        # 2. Agregar categorías configuradas en LocalRepository si existen
        configuraciones = local_repo.listar_configuraciones()
        for clave in configuraciones.keys():
            if clave.startswith("PRESUPUESTO_TECHO_"):
                cat_nombre = (
                    clave.replace("PRESUPUESTO_TECHO_", "").replace("_", " ").title()
                )
                categorias_a_evaluar.add(cat_nombre)

        # Si aún no hay categorías, incluir categorías estándar por defecto
        if not categorias_a_evaluar:
            categorias_a_evaluar.update(
                ["Supermercado", "Combustible", "Servicios", "Comida"]
            )

        items: list[dict[str, Any]] = []
        for cat in sorted(categorias_a_evaluar):
            alerta = evaluar_techo_presupuestario(
                categoria=cat,
                monto_nuevo=0.0,
                sheets_repo=sheets_repo,
                local_repo=local_repo,
            )

            limite = int(alerta.get("limite_presupuesto", 0))
            if limite > 0:
                pct = float(alerta.get("porcentaje_consumido", 0.0))
                alerta_emitida = bool(alerta.get("alerta_emitida", False))

                if pct >= 100.0:
                    estado = "EXCEDIDO"
                elif alerta_emitida:
                    estado = "ALERTA"
                else:
                    estado = "NORMAL"

                item_obj = TechoPresupuestarioItem(
                    categoria=cat,
                    limite_mensual=limite,
                    consumido=int(alerta.get("monto_gastado", 0)),
                    porcentaje=round(pct, 1),
                    umbral_alerta=int(alerta.get("umbral_configurado", 80)),
                    alerta_emitida=alerta_emitida,
                    estado=estado,
                    mensaje=str(alerta.get("mensaje", "")),
                )
                items.append(item_obj.model_dump())

        return jsonify(items), 200
    except Exception as exc:
        logger.error(f"Error consultando techos presupuestarios: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "INTERNAL_ERROR",
                    "mensaje": f"No se pudo evaluar techos presupuestarios: {exc}",
                    "detalles": None,
                }
            ),
            500,
        )
