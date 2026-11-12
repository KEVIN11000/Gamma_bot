from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from api.schemas import CapacidadesResponse, RutaEndpointInfo
from api.security import require_api_key

capacidades_bp = Blueprint("capacidades_v1", __name__)


def _get_version() -> str:
    version_path = Path(__file__).resolve().parent.parent.parent.parent / "VERSION"
    if version_path.exists():
        return version_path.read_text(encoding="utf-8").strip()
    return "2.1.3"


def _limpiar_docstring(doc: str | None) -> str:
    if not doc:
        return ""
    lineas = [line.strip() for line in doc.strip().splitlines() if line.strip()]
    if not lineas:
        return ""
    primera = lineas[0]
    if primera.lower().startswith("class ") or primera.lower().endswith(
        "method/function."
    ):
        if len(lineas) > 1 and not lineas[1].startswith("Args:"):
            return lineas[1]
    return primera


@capacidades_bp.route("/capacidades", methods=["GET"])
@require_api_key
def obtener_capacidades() -> Any:
    """Catálogo y auto-descubrimiento dinámico de endpoints y capacidades del backend."""
    filtro_modulo = request.args.get("modulo", "").strip().lower()

    rutas_info: list[RutaEndpointInfo] = []
    modulos_set: set[str] = set()

    from config import get_disabled_modules, is_module_enabled

    disabled_modules = get_disabled_modules()

    for rule in current_app.url_map.iter_rules():
        rule_str = rule.rule
        if not rule_str.startswith("/api/v1"):
            continue
        if rule.endpoint == "static" or "/static" in rule_str:
            continue

        metodos = sorted([m for m in rule.methods if m not in ("HEAD", "OPTIONS")])
        if not metodos:
            continue

        partes = [p for p in rule_str.replace("/api/v1", "").split("/") if p]
        modulo = partes[0] if partes else "general"
        if modulo.startswith("<"):
            modulo = "general"

        if modulo.lower() in disabled_modules:
            continue
        if rule_str.endswith("/webhooks/whatsapp") and not is_module_enabled(
            "whatsapp"
        ):
            continue

        modulos_set.add(modulo)

        if filtro_modulo and modulo.lower() != filtro_modulo:
            continue

        view_func = current_app.view_functions.get(rule.endpoint)
        descripcion = ""
        if view_func:
            descripcion = _limpiar_docstring(view_func.__doc__)

        parametros = sorted(list(rule.arguments))
        autenticacion = modulo != "webhooks"

        rutas_info.append(
            RutaEndpointInfo(
                modulo=modulo,
                ruta=rule_str,
                metodos=metodos,
                nombre_endpoint=rule.endpoint,
                descripcion=descripcion,
                autenticacion=autenticacion,
                parametros=parametros,
            )
        )

    rutas_info.sort(key=lambda r: (r.modulo, r.ruta, r.metodos[0] if r.metodos else ""))

    version_actual = _get_version()
    capacidades_clave = {
        "presupuesto_fijos_delete": True,
        "presupuesto_techos_put": True,
        "presupuesto_salario_put": True,
        "asistencia_excel_export": True,
        "asistencia_pdf_a4_optimizado": True,
        "asistencia_rectificar_post": True,
        "obligaciones_deuda_foco": True,
        "obligaciones_abonar_post": True,
        "obligaciones_eliminar_delete": True,
        "cierres_historicos_get": True,
        "proyectos_simular_post": True,
        "proyectos_aprobar_post": True,
        "reportes_financiero_pdf": True,
        "reportes_financiero_excel": True,
        "capacidades_discovery": True,
        "whatsapp_webhook_enabled": is_module_enabled("whatsapp"),
    }

    response_obj = CapacidadesResponse(
        version_api=version_actual,
        total_rutas=len(rutas_info),
        modulos=sorted(list(modulos_set)),
        capacidades_clave=capacidades_clave,
        rutas=rutas_info,
    )

    return jsonify(response_obj.model_dump()), 200
