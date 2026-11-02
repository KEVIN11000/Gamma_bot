from __future__ import annotations

import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Set required env vars BEFORE importing flask_app
os.environ["TOKEN"] = "test_token_123"
os.environ["CHAT_ID"] = "123456"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"
os.environ["FLASK_ENV"] = "development"
os.environ["CRON_SECRET"] = "test_cron_secret"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["X_API_KEY"] = "test-secret-key"

# Ensure src is on the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402

from logic.financiero import (  # noqa: E402
    AgenteFinanciero,
    evaluar_techo_presupuestario,
)
from repositories.local_repository import LocalRepository  # noqa: E402


@pytest.fixture
def client() -> Any:
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def local_repo_temp(tmp_path: Any) -> LocalRepository:
    db_file = tmp_path / "presupuesto_test.db"
    return LocalRepository(db_path=db_file)


# ── Tests Unitarios de Evaluación de Techo Presupuestario ───────────────────


def test_alerta_preventiva_alcanza_umbral_80_porciento(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica emisión de alerta preventiva cuando el gasto acumulado alcanza o supera el 80%."""
    # Configuración activa con umbral 80%
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_ALERTAS_ACTIVO", True, tipo="bool"
    )
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_UMBRAL_ALERTA", 80, tipo="int"
    )
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_TECHO_SUPERMERCADO", 1000000, tipo="int"
    )

    # Mockear sheets_repo con 750.000 Gs ya gastados en el mes
    mock_sheets_repo = MagicMock()
    mock_sheets_repo._get_sheet.return_value = None  # Usa fallback a local_repo
    mock_sheets_repo.get_all_movimientos.return_value = [
        {
            "Movimiento": "Gasto",
            "Categoría": "Supermercado",
            "Total": "750000",
            "Mes": "11/2026",
            "Fecha": "01/11/2026",
        }
    ]

    # Nuevo gasto de 100.000 -> Total 850.000 Gs (85% >= 80%)
    res = evaluar_techo_presupuestario(
        categoria="Supermercado",
        monto_nuevo=100000,
        mes=11,
        anio=2026,
        local_repo=local_repo_temp,
        sheets_repo=mock_sheets_repo,
    )

    assert res["activo"] is True
    assert res["alerta_emitida"] is True
    assert res["porcentaje_consumido"] == 85.0
    assert res["monto_gastado"] == 850000
    assert res["limite_presupuesto"] == 1000000
    assert "⚠️ Alerta preventiva: Has alcanzado el 85%" in res["mensaje"]
    assert "Supermercado" in res["mensaje"]


def test_sin_alerta_si_gasto_bajo_umbral(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica que no se emita alerta si el gasto acumulado está por debajo del umbral."""
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_ALERTAS_ACTIVO", True, tipo="bool"
    )
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_UMBRAL_ALERTA", 80, tipo="int"
    )
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_TECHO_COMBUSTIBLE", 500000, tipo="int"
    )

    mock_sheets_repo = MagicMock()
    mock_sheets_repo._get_sheet.return_value = None
    mock_sheets_repo.get_all_movimientos.return_value = [
        {
            "Movimiento": "Gasto",
            "Categoría": "Combustible",
            "Total": "250000",
            "Mes": "11/2026",
        }
    ]

    # Nuevo gasto de 50.000 -> Total 300.000 Gs (60% < 80%)
    res = evaluar_techo_presupuestario(
        categoria="Combustible",
        monto_nuevo=50000,
        mes=11,
        anio=2026,
        local_repo=local_repo_temp,
        sheets_repo=mock_sheets_repo,
    )

    assert res["activo"] is True
    assert res["alerta_emitida"] is False
    assert res["porcentaje_consumido"] == 60.0
    assert res["monto_gastado"] == 300000
    assert "Presupuesto bajo control" in res["mensaje"]


def test_feature_toggle_desactivado_no_emite_alerta(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica que si PRESUPUESTO_ALERTAS_ACTIVO='false', no se emita alerta aunque se supere el 100%."""
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_ALERTAS_ACTIVO", False, tipo="bool"
    )
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_TECHO_VARIOS", 200000, tipo="int"
    )

    mock_sheets_repo = MagicMock()
    mock_sheets_repo.get_all_movimientos.return_value = []

    # Gasto de 250.000 sobre límite de 200.000 (125%)
    res = evaluar_techo_presupuestario(
        categoria="Varios",
        monto_nuevo=250000,
        local_repo=local_repo_temp,
        sheets_repo=mock_sheets_repo,
    )

    assert res["activo"] is False
    assert res["alerta_emitida"] is False
    assert "desactivadas" in res["mensaje"]


def test_umbral_dinamico_configurable(
    local_repo_temp: LocalRepository,
) -> None:
    """Verifica que la alerta respete umbrales dinámicos distintos (ej. 90% en vez de 80%)."""
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_ALERTAS_ACTIVO", True, tipo="bool"
    )
    # Cambiamos umbral a 90%
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_UMBRAL_ALERTA", 90, tipo="int"
    )
    local_repo_temp.establecer_configuracion(
        "PRESUPUESTO_TECHO_OCIO", 1000000, tipo="int"
    )

    mock_sheets_repo = MagicMock()
    mock_sheets_repo._get_sheet.return_value = None
    mock_sheets_repo.get_all_movimientos.return_value = [
        {
            "Movimiento": "Gasto",
            "Categoría": "Ocio",
            "Total": "850000",
            "Mes": "11/2026",
        }
    ]

    # Gasto al 85%: Con umbral 90%, NO debe disparar alerta
    res_85 = evaluar_techo_presupuestario(
        categoria="Ocio",
        monto_nuevo=0,
        mes=11,
        anio=2026,
        local_repo=local_repo_temp,
        sheets_repo=mock_sheets_repo,
    )
    assert res_85["alerta_emitida"] is False
    assert res_85["umbral_configurado"] == 90

    # Agregamos 70.000 -> Total 920.000 (92% >= 90%): AHORA SÍ debe disparar
    res_92 = evaluar_techo_presupuestario(
        categoria="Ocio",
        monto_nuevo=70000,
        mes=11,
        anio=2026,
        local_repo=local_repo_temp,
        sheets_repo=mock_sheets_repo,
    )
    assert res_92["alerta_emitida"] is True
    assert res_92["porcentaje_consumido"] == 92.0


# ── Tests de Integración: Bot y API REST ────────────────────────────────────


def test_integracion_registrar_movimiento_bot_anexa_alerta() -> None:
    """Verifica que AgenteFinanciero.registrar_movimiento anexe la alerta preventiva en el mensaje del bot."""
    agente = AgenteFinanciero(spreadsheet_id="dummy_sheet")
    setattr(agente, "_ws", MagicMock())

    fake_alerta = {
        "activo": True,
        "alerta_emitida": True,
        "categoria": "Farmacia",
        "porcentaje_consumido": 82.0,
        "mensaje": "⚠️ Alerta preventiva: Has alcanzado el 82% de tu presupuesto en Farmacia.",
    }

    with patch.object(agente, "evaluar_techo_presupuestario", return_value=fake_alerta):
        mensaje = agente.registrar_movimiento(
            {
                "fecha": "02/11",
                "tipo_movimiento": "Gasto",
                "proveedor_cliente": "Farmacia Catedral",
                "total": 150000,
                "categoria": "Farmacia",
            }
        )

        assert "✅ Movimiento guardado en Libro Diario" in mensaje
        assert "🔴 Gasto" in mensaje
        assert (
            "⚠️ Alerta preventiva: Has alcanzado el 82% de tu presupuesto en Farmacia."
            in mensaje
        )


def test_integracion_api_post_movimiento_incluye_alerta(client: Any) -> None:
    """Verifica que POST /api/v1/movimientos adjunte 'alerta_presupuesto' en el JSON si se supera el umbral."""
    fake_alerta = {
        "activo": True,
        "alerta_emitida": True,
        "categoria": "Restaurantes",
        "porcentaje_consumido": 88.0,
        "monto_gastado": 440000,
        "limite_presupuesto": 500000,
        "mensaje": "⚠️ Alerta preventiva: Has alcanzado el 88% de tu presupuesto en Restaurantes.",
    }

    with patch(
        "logic.financiero.evaluar_techo_presupuestario", return_value=fake_alerta
    ), patch("repositories.sheets_repository.SheetsRepository._get_sheet"):
        res = client.post(
            "/api/v1/movimientos",
            headers={"X-API-KEY": "test-secret-key"},
            json={
                "tipo": "Gasto",
                "concepto": "Cena Familiar",
                "monto": 200000,
                "categoria": "Restaurantes",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["tipo"] == "Gasto"
        assert "alerta_presupuesto" in data
        assert data["alerta_presupuesto"]["alerta_emitida"] is True
        assert data["alerta_presupuesto"]["porcentaje_consumido"] == 88.0
        assert "⚠️ Alerta preventiva" in data["alerta_presupuesto"]["mensaje"]
