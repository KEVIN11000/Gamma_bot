from __future__ import annotations

from unittest.mock import patch

import pytest

from services.presupuesto_service import (
    despachar_alerta_presupuestaria_proactiva,
    reset_presupuesto_cooldown,
    formatear_monto_gs,
)


@pytest.fixture(autouse=True)
def clean_cooldown():
    """Limpia el almacén de cooldown antes y después de cada prueba."""
    reset_presupuesto_cooldown()
    yield
    reset_presupuesto_cooldown()


class TestPresupuestoAlertasService:
    """Suite de pruebas unitarias para alertas presupuestarias proactivas."""

    def test_formatear_monto_gs(self):
        """Verifica formateo estándar en Guaraníes con puntos."""
        assert formatear_monto_gs(1500000) == "1.500.000 Gs"
        assert formatear_monto_gs(45000) == "45.000 Gs"

    @patch("logic.financiero.evaluar_techo_presupuestario")
    @patch("app_queue.worker.enqueue")
    def test_alerta_emitida_al_superar_umbral(self, mock_enqueue, mock_evaluar):
        """Verifica emisión y encolado de alerta al superar el techo presupuestario."""
        mock_enqueue.return_value = 501
        mock_evaluar.return_value = {
            "activo": True,
            "alerta_emitida": True,
            "categoria": "Supermercado",
            "porcentaje_consumido": 85.0,
            "monto_gastado": 1700000,
            "limite_presupuesto": 2000000,
            "mensaje": "Alcanzó el 85% de Supermercado.",
        }

        res = despachar_alerta_presupuestaria_proactiva(
            categoria="Supermercado",
            monto_nuevo=300000,
            recipient_id="12345678",
            channel="telegram",
            custom_now=1000000.0,
        )

        assert res["emitida"] is True
        assert res["job_id"] == 501
        assert "⚠️ *Alerta Presupuestaria: Supermercado*" in res["mensaje"]
        assert "85.0%" in res["mensaje"]
        assert "1.700.000 Gs" in res["mensaje"]

        mock_enqueue.assert_called_once()
        kwargs = mock_enqueue.call_args[1]
        assert kwargs["recipient_id"] == "12345678"
        assert kwargs["operacion"] == "enviar_notificacion"
        assert kwargs["channel"] == "telegram"
        assert "1.700.000 Gs" in kwargs["payload"]["mensaje"]

    @patch("logic.financiero.evaluar_techo_presupuestario")
    @patch("app_queue.worker.enqueue")
    def test_cooldown_suprime_segunda_alerta_en_24h(self, mock_enqueue, mock_evaluar):
        """Verifica que una segunda alerta en la misma categoría se suprima dentro de las 24 horas."""
        mock_enqueue.return_value = 502
        mock_evaluar.return_value = {
            "activo": True,
            "alerta_emitida": True,
            "categoria": "Comida",
            "porcentaje_consumido": 90.0,
            "monto_gastado": 900000,
            "limite_presupuesto": 1000000,
        }

        t0 = 1700000000.0
        # 1. Primera alerta emitida
        res1 = despachar_alerta_presupuestaria_proactiva(
            categoria="Comida",
            monto_nuevo=50000,
            recipient_id="user_1",
            custom_now=t0,
        )
        assert res1["emitida"] is True
        assert mock_enqueue.call_count == 1

        # 2. Segunda alerta 2 horas después (7200s < 86400s)
        res2 = despachar_alerta_presupuestaria_proactiva(
            categoria="Comida",
            monto_nuevo=30000,
            recipient_id="user_1",
            custom_now=t0 + 7200.0,
        )
        assert res2["emitida"] is False
        assert res2["motivo"] == "cooldown_activo"
        assert mock_enqueue.call_count == 1  # No se volvió a encolar

    @patch("logic.financiero.evaluar_techo_presupuestario")
    @patch("app_queue.worker.enqueue")
    def test_alerta_emitida_despues_de_24h(self, mock_enqueue, mock_evaluar):
        """Verifica que transcurrido el cooldown de 24 horas, la alerta se vuelva a emitir."""
        mock_enqueue.return_value = 503
        mock_evaluar.return_value = {
            "activo": True,
            "alerta_emitida": True,
            "categoria": "Combustible",
            "porcentaje_consumido": 82.0,
            "monto_gastado": 820000,
            "limite_presupuesto": 1000000,
        }

        t0 = 1700000000.0
        # Alerta 1
        despachar_alerta_presupuestaria_proactiva(
            categoria="Combustible",
            recipient_id="user_1",
            custom_now=t0,
        )
        assert mock_enqueue.call_count == 1

        # Alerta 2 tras 24h y 1 segundo (86401s)
        res_despues = despachar_alerta_presupuestaria_proactiva(
            categoria="Combustible",
            recipient_id="user_1",
            custom_now=t0 + 86401.0,
        )
        assert res_despues["emitida"] is True
        assert mock_enqueue.call_count == 2

    @patch("logic.financiero.evaluar_techo_presupuestario")
    @patch("app_queue.worker.enqueue")
    def test_diferentes_categorias_tienen_cooldown_independiente(
        self, mock_enqueue, mock_evaluar
    ):
        """Verifica que el cooldown sea por categoría y no bloquee otras categorías distintas."""
        mock_enqueue.return_value = 504
        mock_evaluar.return_value = {
            "activo": True,
            "alerta_emitida": True,
            "porcentaje_consumido": 88.0,
            "monto_gastado": 880000,
            "limite_presupuesto": 1000000,
        }

        t0 = 1700000000.0
        # Alerta en Supermercado
        res_super = despachar_alerta_presupuestaria_proactiva(
            categoria="Supermercado",
            recipient_id="user_1",
            custom_now=t0,
        )
        assert res_super["emitida"] is True

        # Alerta inmediata en Farmacia (no debe ser bloqueada por Supermercado)
        res_farma = despachar_alerta_presupuestaria_proactiva(
            categoria="Farmacia",
            recipient_id="user_1",
            custom_now=t0 + 60.0,
        )
        assert res_farma["emitida"] is True
        assert mock_enqueue.call_count == 2

    @patch("logic.financiero.evaluar_techo_presupuestario")
    @patch("app_queue.worker.enqueue")
    def test_alerta_no_emitida_si_dentro_del_limite(self, mock_enqueue, mock_evaluar):
        """Verifica que si no superó el umbral no se encole ninguna notificación."""
        mock_evaluar.return_value = {
            "activo": True,
            "alerta_emitida": False,
            "porcentaje_consumido": 45.0,
            "monto_gastado": 450000,
            "limite_presupuesto": 1000000,
        }

        res = despachar_alerta_presupuestaria_proactiva(
            categoria="Ocio",
            monto_nuevo=50000,
        )
        assert res["emitida"] is False
        assert res["motivo"] == "dentro_de_limite"
        mock_enqueue.assert_not_called()

    @patch("logic.financiero.evaluar_techo_presupuestario")
    @patch("app_queue.worker.enqueue")
    def test_despacho_canal_whatsapp(self, mock_enqueue, mock_evaluar):
        """Verifica que el parámetro de canal WhatsApp se transfiera correctamente a la cola."""
        mock_enqueue.return_value = 505
        mock_evaluar.return_value = {
            "activo": True,
            "alerta_emitida": True,
            "categoria": "Servicios",
            "porcentaje_consumido": 95.0,
            "monto_gastado": 950000,
            "limite_presupuesto": 1000000,
        }

        res = despachar_alerta_presupuestaria_proactiva(
            categoria="Servicios",
            recipient_id="595981123456@s.whatsapp.net",
            channel="whatsapp",
        )
        assert res["emitida"] is True
        mock_enqueue.assert_called_once()
        assert (
            mock_enqueue.call_args[1]["recipient_id"] == "595981123456@s.whatsapp.net"
        )
        assert mock_enqueue.call_args[1]["channel"] == "whatsapp"

    def test_categoria_vacia_no_emite(self):
        """Verifica que categoría vacía retorne rechazo inmediato."""
        res = despachar_alerta_presupuestaria_proactiva(categoria="   ")
        assert res["emitida"] is False
        assert res["motivo"] == "categoria_vacia"
