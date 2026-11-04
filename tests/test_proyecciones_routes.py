from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from api.schemas import FlujoCajaResponse, FlujoCajaItemDiario

# Set required env vars BEFORE importing flask_app
os.environ.setdefault("TOKEN", "test_token_123")
os.environ.setdefault("CHAT_ID", "123456")
os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402


def _get_valid_api_key() -> str:
    return os.getenv("X_API_KEY") or os.getenv("GAMMA_MOBILE_API_KEY") or "dev-key"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestProyeccionesRoutes:
    """Verifica el endpoint GET /api/v1/proyecciones/flujo-caja."""

    def test_proyecciones_unauthorized_without_key(self, client):
        """Verifica que sin X-API-KEY devuelva 401."""
        resp = client.get("/api/v1/proyecciones/flujo-caja")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_proyecciones_unauthorized_invalid_key(self, client):
        """Verifica que con X-API-KEY inválida devuelva 401."""
        resp = client.get(
            "/api/v1/proyecciones/flujo-caja",
            headers={"X-API-KEY": "invalid-secret-key"},
        )
        assert resp.status_code == 401

    def test_proyecciones_success_default(self, client):
        """Verifica retorno 200 con payload estructurado y headers anti-cache."""
        resp = client.get(
            "/api/v1/proyecciones/flujo-caja",
            headers={"X-API-KEY": _get_valid_api_key()},
        )
        assert resp.status_code == 200
        assert "no-store" in resp.headers.get("Cache-Control", "")

        data = resp.get_json()
        assert "saldo_actual" in data
        assert "saldo_proyectado_30d" in data
        assert "dias" in data
        assert len(data["dias"]) == 30
        assert "dias_criticos" in data

    def test_proyecciones_with_query_params(self, client):
        """Verifica cálculo con saldo_inicial y gasto_diario personalizados."""
        resp = client.get(
            "/api/v1/proyecciones/flujo-caja?saldo_inicial=500000&gasto_diario=10000&umbral_reserva=250000",
            headers={"X-API-KEY": _get_valid_api_key()},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["saldo_actual"] == 500000.0
        assert data["total_gastos_variables_estimados"] == 300000.0
        assert data["saldo_proyectado_30d"] == 200000.0
        # Umbral reserva es 250.000, al caer a 200.000 debe reportar días críticos
        assert len(data["dias_criticos"]) > 0

    def test_flujo_caja_dto_validation(self):
        """Verifica serialización y validación estricta de esquemas Pydantic."""
        item = FlujoCajaItemDiario(
            fecha="2026-11-01",
            saldo_inicial=100000.0,
            ingresos=50000.0,
            egresos_fijos=20000.0,
            egresos_variables=10000.0,
            saldo_final=120000.0,
            compromisos=["ANDE"],
        )
        assert item.saldo_final == 120000.0

        resp = FlujoCajaResponse(
            saldo_actual=100000.0,
            saldo_proyectado_30d=120000.0,
            total_ingresos_proyectados=50000.0,
            total_gastos_fijos=20000.0,
            total_gastos_variables_estimados=10000.0,
            dias_criticos=[],
            dias=[item],
        )
        assert resp.saldo_proyectado_30d == 120000.0

        with pytest.raises(ValidationError):
            FlujoCajaItemDiario(fecha="2026-11-01")  # Faltan campos requeridos
