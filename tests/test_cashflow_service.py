from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from services.cashflow_service import (
    CashFlowProjector,
    ResultadoFlujoCaja,
)


class TestCashFlowProjector:
    """Suite de pruebas unitarias para CashFlowProjector."""

    def test_proyectar_30_dias_balance_plano(self):
        """Verifica que sin movimientos el saldo se mantenga idéntico durante los 30 días."""
        projector = CashFlowProjector()
        res = projector.proyectar_30_dias(
            saldo_inicial=1000000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=[],
            gasto_diario_estimado=0.0,
        )

        assert isinstance(res, ResultadoFlujoCaja)
        assert len(res.dias) == 30
        assert res.saldo_actual == 1000000.0
        assert res.saldo_proyectado_30d == 1000000.0
        assert res.total_ingresos_proyectados == 0.0
        assert res.total_gastos_fijos == 0.0
        assert res.total_gastos_variables_estimados == 0.0
        assert len(res.dias_criticos) == 0

    def test_proyectar_con_gastos_variables_diarios(self):
        """Verifica el descuento acumulativo de gasto diario estimado."""
        projector = CashFlowProjector()
        res = projector.proyectar_30_dias(
            saldo_inicial=300000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=[],
            gasto_diario_estimado=10000.0,
        )

        assert res.total_gastos_variables_estimados == 300000.0
        assert res.saldo_proyectado_30d == 0.0
        assert res.dias[0].saldo_final == 290000.0
        assert res.dias[-1].saldo_final == 0.0

    def test_proyectar_con_obligaciones_fijas(self):
        """Verifica la deducción de compromisos fijos en su fecha de vencimiento."""
        projector = CashFlowProjector()
        obligaciones = [
            {
                "concepto": "Internet Fibra",
                "monto": 150000.0,
                "vencimiento": "2026-11-10",
            },
            {
                "concepto": "Alquiler",
                "monto": 1200000.0,
                "vencimiento": "2026-11-05",
            },
        ]
        res = projector.proyectar_30_dias(
            saldo_inicial=2000000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=obligaciones,
            gasto_diario_estimado=0.0,
        )

        assert res.total_gastos_fijos == 1350000.0
        assert res.saldo_proyectado_30d == 650000.0

        # Verificar que Alquiler se imputó el 5 de noviembre
        dia_5 = next(d for d in res.dias if d.fecha == "2026-11-05")
        assert dia_5.egresos_fijos == 1200000.0
        assert any("Alquiler" in c for c in dia_5.compromisos)

    def test_proyectar_con_ingreso_programado(self):
        """Verifica el impacto positivo de ingresos calendarizados."""
        projector = CashFlowProjector()
        ingresos = [
            {"concepto": "Salario Quincena", "monto": 1500000.0, "dia": 15},
        ]
        res = projector.proyectar_30_dias(
            saldo_inicial=200000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=ingresos,
            obligaciones_fijas=[],
            gasto_diario_estimado=0.0,
        )

        assert res.total_ingresos_proyectados == 1500000.0
        assert res.saldo_proyectado_30d == 1700000.0
        dia_15 = next(d for d in res.dias if d.fecha == "2026-11-15")
        assert dia_15.ingresos == 1500000.0

    def test_dias_criticos_detectados_ante_saldo_negativo(self):
        """Verifica la detección de días con déficit financiero."""
        projector = CashFlowProjector()
        obligaciones = [
            {"concepto": "Préstamo", "monto": 600000.0, "vencimiento": "2026-11-04"}
        ]
        res = projector.proyectar_30_dias(
            saldo_inicial=200000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=obligaciones,
            gasto_diario_estimado=0.0,
            umbral_reserva_minima=0.0,
        )

        assert len(res.dias_criticos) > 0
        primer_critico = res.dias_criticos[0]
        assert primer_critico["fecha"] == "2026-11-04"
        assert primer_critico["saldo"] == -400000.0
        assert primer_critico["deficit"] == 400000.0

    def test_umbral_reserva_minima(self):
        """Verifica alerta si el saldo cae por debajo de la reserva mínima deseada."""
        projector = CashFlowProjector()
        res = projector.proyectar_30_dias(
            saldo_inicial=500000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=[
                {"concepto": "Gasto", "monto": 200000.0, "vencimiento": "2026-11-02"}
            ],
            gasto_diario_estimado=0.0,
            umbral_reserva_minima=400000.0,
        )

        # Saldo final 300.000 < 400.000 -> Día crítico por reserva
        assert len(res.dias_criticos) > 0
        critico = res.dias_criticos[0]
        assert critico["fecha"] == "2026-11-02"
        assert critico["saldo"] == 300000.0
        assert critico["deficit"] == 100000.0

    def test_resiliencia_obligacion_fecha_invalida_o_vacia(self):
        """Verifica que fechas erróneas o vacías se normalicen de forma segura sin excepción."""
        projector = CashFlowProjector()
        obligaciones = [
            {"concepto": "Servicio sin fecha", "monto": 100000.0, "vencimiento": ""},
            {
                "concepto": "Servicio fecha rota",
                "monto": 50000.0,
                "vencimiento": "fecha_invalida",
            },
        ]
        res = projector.proyectar_30_dias(
            saldo_inicial=1000000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=obligaciones,
            gasto_diario_estimado=0.0,
        )

        assert res.total_gastos_fijos == 150000.0
        assert res.saldo_proyectado_30d == 850000.0

    def test_obligaciones_pagadas_son_ignoradas(self):
        """Verifica que las obligaciones marcadas como pagadas o canceladas no se descuenten."""
        projector = CashFlowProjector()
        obligaciones = [
            {
                "concepto": "Deuda 1",
                "monto": 300000.0,
                "vencimiento": "2026-11-05",
                "pagado": True,
            },
            {
                "concepto": "Deuda 2",
                "monto": 400000.0,
                "vencimiento": "2026-11-08",
                "estado": "saldado",
            },
            {
                "concepto": "Deuda 3",
                "monto": 250000.0,
                "vencimiento": "2026-11-12",
                "estado": "pendiente",
            },
        ]
        res = projector.proyectar_30_dias(
            saldo_inicial=1000000.0,
            fecha_inicio=date(2026, 11, 1),
            ingresos_esperados=[],
            obligaciones_fijas=obligaciones,
            gasto_diario_estimado=0.0,
        )

        # Solo Deuda 3 debe computarse
        assert res.total_gastos_fijos == 250000.0
        assert res.saldo_proyectado_30d == 750000.0

    def test_obtener_obligaciones_desde_sheets_repo_mock(self):
        """Verifica la carga automática desde el mock de SheetsRepository."""
        mock_sheets = MagicMock()
        mock_ws = MagicMock()
        mock_ws.get_all_values.return_value = [
            ["Concepto", "Monto", "Vencimiento", "Estado"],
            ["ANDE Luz", "200.000", "15/11/2026", "Pendiente"],
            ["Tigo Internet", "180.000", "20/11/2026", "Pendiente"],
            ["Deuda Pagada", "500.000", "01/11/2026", "Pagado"],
        ]
        mock_sheets._get_sheet.return_value = mock_ws

        projector = CashFlowProjector(sheets_repo=mock_sheets)
        obs = projector._obtener_obligaciones_activas()

        assert len(obs) == 2
        assert obs[0]["concepto"] == "ANDE Luz"
        assert obs[0]["monto"] == 200000.0
        assert obs[1]["concepto"] == "Tigo Internet"
        assert obs[1]["monto"] == 180000.0

    def test_to_dict_serializacion(self):
        """Verifica que to_dict retorne estructura serializable a JSON."""
        projector = CashFlowProjector()
        res = projector.proyectar_30_dias(
            saldo_inicial=500000.0,
            fecha_inicio=date(2026, 11, 1),
        )
        d = res.to_dict()
        assert isinstance(d, dict)
        assert d["saldo_actual"] == 500000.0
        assert "dias" in d
        assert len(d["dias"]) == 30
        assert "dias_criticos" in d
