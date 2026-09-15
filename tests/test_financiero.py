import unittest
import os
from unittest.mock import patch

from logic.financiero import (
    create_debt,
    get_active_debts,
    register_payment,
    execute_monthly_closing,
    simulate_project,
    approve_project,
    calcular_margen_de_ataque,
    proyectar_cola_deudas,
    simular_impacto_abono
)

class TestFinancieroLogic(unittest.TestCase):

    @patch('logic.financiero.SheetsRepository')
    @patch('logic.financiero.CalendarService')
    def test_create_debt(self, MockCalendar, MockRepo):
        repo_instance = MockRepo.return_value
        debt_id = create_debt("Banco X", "Prestamo", 10000, 12, "2026-10-01")
        self.assertIsNotNone(debt_id)
        repo_instance.insert_obligacion.assert_called_once()
        MockCalendar.create_event.assert_called_once()

    @patch('logic.financiero.SheetsRepository')
    def test_get_active_debts(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_obligaciones_activas.return_value = [{"ID_Obligacion": "123", "Estado": "Activo"}]
        
        debts = get_active_debts()
        self.assertEqual(len(debts), 1)
        
        debts = get_active_debts(debt_id="123")
        self.assertEqual(len(debts), 1)
        
        debts = get_active_debts(debt_id="456")
        self.assertEqual(len(debts), 0)

    @patch('logic.financiero.SheetsRepository')
    @patch('logic.financiero.CalendarService')
    def test_register_payment(self, MockCalendar, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_obligacion_by_id.return_value = {
            "ID_Obligacion": "123",
            "Saldo_Actual": "100000",
            "Cuotas_Restantes": "5",
            "Event_ID": "evt_1"
        }
        
        register_payment("123", 100000, "2026-09-04")
        
        repo_instance.insert_movimiento_diario.assert_called_once()
        repo_instance.update_obligacion_saldo.assert_called_once_with("123", 0, 4, "Saldada")
        MockCalendar.mark_event_completed.assert_called_once_with("evt_1")

    @patch('logic.financiero.SheetsRepository')
    @patch('logic.financiero.DriveService')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_execute_monthly_closing(self, mock_open, MockDrive, MockRepo):
        repo_instance = MockRepo.return_value
        
        # Test case 1
        repo_instance.get_movimientos_mes.return_value = [
            {"Tipo_Movimiento": "Ingreso", "Monto_Total": 1000, "Monto_IVA": 100, "Clasificacion_IVA": "Débito Fiscal"},
            {"Tipo_Movimiento": "Egreso", "Monto_Total": 200, "Monto_IVA": 20, "Clasificacion_IVA": "Crédito Fiscal"}
        ]
        repo_instance.get_last_cierre_mensual.return_value = {"Saldo_Acumulado_Actual": 500}
        MockDrive.upload_backup.return_value = "mock_drive_id"
        
        drive_id = execute_monthly_closing(9, 2026)
        self.assertEqual(drive_id, "mock_drive_id")
        
        repo_instance.insert_cierre_mensual.assert_called_once()
        repo_instance.insert_cierre_mensual.reset_mock()

        # Test case 2
        repo_instance.get_movimientos_mes.return_value = [
            {"Tipo_Movimiento": "Ingreso", "Monto_Total": 500, "Monto_IVA": 50, "Clasificacion_IVA": "Débito Fiscal"},
            {"Tipo_Movimiento": "Egreso", "Monto_Total": 800, "Monto_IVA": 80, "Clasificacion_IVA": "Crédito Fiscal"}
        ]
        repo_instance.get_last_cierre_mensual.return_value = {}
        
        execute_monthly_closing(10, 2026)
        repo_instance.insert_cierre_mensual.assert_called_once()

    @patch('logic.financiero.SheetsRepository')
    def test_simulate_project(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_presupuesto_base.return_value = {"ingresos": 5000}
        repo_instance.get_obligaciones_activas.return_value = []
        
        project_id = simulate_project(1000, 12, "Auto")
        self.assertIsNotNone(project_id)
        repo_instance.insert_obligacion.assert_called_once()

    @patch('logic.financiero.SheetsRepository')
    def test_approve_project(self, MockRepo):
        repo_instance = MockRepo.return_value
        approve_project("789")
        repo_instance.update_obligacion_estado.assert_called_once_with("789", "Activo")

    @patch('logic.financiero.SheetsRepository')
    def test_calcular_margen_de_ataque(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.obtener_presupuesto_base_completo.return_value = (10000, 3000)
        repo_instance.get_obligaciones_activas.return_value = [
            {"Cuota_Referencia_Gs": "2000"},
            {"Cuota_Referencia_Gs": "1000"}
        ]
        margen = calcular_margen_de_ataque()
        self.assertEqual(margen, 4000)

    @patch('logic.financiero.SheetsRepository')
    @patch('logic.logic.get_now_py')
    def test_proyectar_cola_deudas(self, mock_get_now, MockRepo):
        import datetime
        from dateutil.tz import tzutc
        mock_get_now.return_value = datetime.datetime(2026, 9, 15, tzinfo=tzutc())
        
        repo_instance = MockRepo.return_value
        repo_instance.obtener_presupuesto_base_completo.return_value = (10000, 3000)
        repo_instance.get_obligaciones_activas.return_value = [
            {"ID_Obligacion": "1", "Nombre": "D1", "Saldo_Actual": 1000, "Cuota_Referencia_Gs": 100, "Orden_Prioridad": 2, "Dia_Vencimiento": 10}, 
            {"ID_Obligacion": "2", "Nombre": "D2", "Saldo_Actual": 2000, "Cuota_Referencia_Gs": 200, "Orden_Prioridad": 1, "Dia_Vencimiento": 20}, 
            {"ID_Obligacion": "3", "Nombre": "D3", "Saldo_Actual": 3000, "Cuota_Referencia_Gs": 300, "Orden_Prioridad": 3, "Dia_Vencimiento": 18}  
        ]
        
        res = proyectar_cola_deudas(criterio="prioridad")
        self.assertIn("proyeccion", res)
        # D1 is vencida, should be first
        self.assertEqual(res["proyeccion"][0]["nombre"], "D1")
        # D2 has higher priority than D3
        self.assertEqual(res["proyeccion"][1]["nombre"], "D2")
        self.assertEqual(res["proyeccion"][2]["nombre"], "D3")

    @patch('logic.financiero.SheetsRepository')
    def test_simular_impacto_abono(self, MockRepo):
        repo_instance = MockRepo.return_value
        
        # Test zero division avoidance
        repo_instance.get_obligacion_by_id.return_value = {
            "Saldo_Actual": "5000",
            "Cuota_Referencia_Gs": "0"
        }
        res = simular_impacto_abono(1000, "999")
        self.assertEqual(res, {"error": "Cuota base es 0"})
        
        repo_instance.get_obligacion_by_id.return_value = {
            "Saldo_Actual": "5000",
            "Cuota_Referencia_Gs": "1000"
        }
        res = simular_impacto_abono(2000, "999")
        self.assertEqual(res["saldo_nuevo"], 3000)
        self.assertEqual(res["meses_restantes"], 3)

if __name__ == '__main__':
    unittest.main()
