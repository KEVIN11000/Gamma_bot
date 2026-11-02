from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify

from api.schemas import ClimaResponse
from api.security import require_api_key

clima_bp = Blueprint("clima_v1", __name__)


@clima_bp.route("/clima", methods=["GET"])
@require_api_key
def get_clima() -> Any:
    """
    Retorna el pronóstico climático de Asunción y alerta de paraguas
    para la pantalla principal de Gamma Mobile.
    """
    from logic.cron_jobs import obtener_datos_clima

    datos = obtener_datos_clima()
    resp_obj = ClimaResponse(**datos)
    return jsonify(resp_obj.model_dump()), 200
