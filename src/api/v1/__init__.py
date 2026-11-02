from __future__ import annotations

from flask import Blueprint

from api.v1.routes_asistencia import asistencia_bp
from api.v1.routes_avisos import avisos_bp
from api.v1.routes_cierres import cierres_bp
from api.v1.routes_clima import clima_bp
from api.v1.routes_dashboard import dashboard_bp
from api.v1.routes_health import health_bp
from api.v1.routes_movimientos import movimientos_bp
from api.v1.routes_obligaciones import obligaciones_bp
from api.v1.routes_soporte import soporte_bp

v1_bp = Blueprint("mobile_api", __name__)

v1_bp.register_blueprint(health_bp)
v1_bp.register_blueprint(dashboard_bp)
v1_bp.register_blueprint(asistencia_bp)
v1_bp.register_blueprint(movimientos_bp)
v1_bp.register_blueprint(obligaciones_bp)
v1_bp.register_blueprint(avisos_bp)
v1_bp.register_blueprint(cierres_bp)
v1_bp.register_blueprint(clima_bp)
v1_bp.register_blueprint(soporte_bp)

__all__ = [
    "v1_bp",
    "health_bp",
    "dashboard_bp",
    "asistencia_bp",
    "movimientos_bp",
    "obligaciones_bp",
    "avisos_bp",
    "cierres_bp",
    "clima_bp",
    "soporte_bp",
]
