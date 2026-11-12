from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from api.schemas import ParseMovementRequest, ParsedMovement

# Set required env vars BEFORE importing flask_app
os.environ.setdefault("TOKEN", "test_token_123")
os.environ.setdefault("CHAT_ID", "123456")
os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")
os.environ.setdefault("X_API_KEY", "test-secret-key")

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402


def _get_valid_api_key() -> str:
    return (
        os.getenv("X_API_KEY") or os.getenv("GAMMA_MOBILE_API_KEY") or "test-secret-key"
    )


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestNLPRoutes:
    """Tests para endpoint POST /api/v1/movimientos/parse y esquemas DTO."""

    def test_parse_route_unauthorized_without_key(self, client):
        """Verifica que sin X-API-KEY retorne 401."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            json={"texto": "Gasto 50000 en Don Vito"},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_parse_route_unauthorized_invalid_key(self, client):
        """Verifica que con X-API-KEY errónea retorne 401."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            headers={"X-API-KEY": "wrong-key-completely-invalid"},
            json={"texto": "Gasto 50000 en Don Vito"},
        )
        assert resp.status_code == 401

    def test_parse_route_valid_gasto(self, client):
        """Verifica parsing exitoso de un gasto común."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            headers={"X-API-KEY": _get_valid_api_key()},
            json={"texto": "Gasto 45.000 almuerzo en Don Vito"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valido"] is True
        assert data["tipo_movimiento"] == "Gasto"
        assert data["monto"] == 45000.0
        assert data["categoria"] == "Comida"
        assert data["proveedor_cliente"] == "Don Vito"
        assert data["confianza"] >= 0.70

    def test_parse_route_valid_ingreso(self, client):
        """Verifica parsing exitoso de un ingreso."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            headers={"X-API-KEY": _get_valid_api_key()},
            json={"texto": "Ingreso 2M sueldo"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["valido"] is True
        assert data["tipo_movimiento"] == "Ingreso"
        assert data["monto"] == 2000000.0
        assert data["categoria"] == "Sueldo"

    def test_parse_route_validation_error_empty_text(self, client):
        """Verifica que texto vacío o menor a 2 caracteres devuelva 422."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            headers={"X-API-KEY": _get_valid_api_key()},
            json={"texto": ""},
        )
        assert resp.status_code == 422
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_parse_route_validation_error_missing_texto(self, client):
        """Verifica que payload sin 'texto' devuelva 422."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            headers={"X-API-KEY": _get_valid_api_key()},
            json={},
        )
        assert resp.status_code == 422
        data = resp.get_json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_parse_route_validation_error_not_dict(self, client):
        """Verifica que payload que no sea JSON dict devuelva 422."""
        resp = client.post(
            "/api/v1/movimientos/parse",
            headers={
                "X-API-KEY": _get_valid_api_key(),
                "Content-Type": "application/json",
            },
            data="12345",
        )
        assert resp.status_code == 422

    def test_parse_schemas_validation(self):
        """Verifica validación de modelos Pydantic directamente."""
        req = ParseMovementRequest(texto="Pague 20k farmacia")
        assert req.texto == "Pague 20k farmacia"

        with pytest.raises(ValidationError):
            ParseMovementRequest(texto="a")

        parsed = ParsedMovement(
            valido=True,
            tipo_movimiento="Gasto",
            monto=20000.0,
            categoria="Salud",
            proveedor_cliente="S/N",
            descripcion="Farmacia",
            confianza=0.85,
        )
        assert parsed.valido is True
        assert parsed.monto == 20000.0
