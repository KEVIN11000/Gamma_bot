import unittest
import os
from unittest.mock import patch

# Ensure we don't write to /tmp on Windows during tests, but our code hardcodes /tmp,
# so we mock open or just let it fail/write to the C: drive if it can. 
# Better to mock open.
from src.logic.financiero import (
    create_debt,
    get_active_debts,
    register_payment,
    execute_monthly_closing,
    simulate_project,
    approve_project
)

class TestFinancieroLogic(unittest.TestCase):

    @patch('src.logic.financiero.SheetsRepository')
    @patch('src.logic.financiero.CalendarService')
    def test_create_debt(self, MockCalendar, MockRepo):
        repo_instance = MockRepo.return_value
        debt_id = create_debt("Banco X", "Prestamo", 10000, 12, "2026-10-01")
        self.assertIsNotNone(debt_id)
        repo_instance.insert_obligacion.assert_called_once()
        MockCalendar.create_event.assert_called_once()

    @patch('src.logic.financiero.SheetsRepository')
    def test_get_active_debts(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_obligaciones_activas.return_value = [{"ID_Obligacion": "123", "Estado": "Activo"}]
        
        debts = get_active_debts()
        self.assertEqual(len(debts), 1)
        
        debts = get_active_debts(debt_id="123")
        self.assertEqual(len(debts), 1)
        
        debts = get_active_debts(debt_id="456")
        self.assertEqual(len(debts), 0)

    @patch('src.logic.financiero.SheetsRepository')
    @patch('src.logic.financiero.CalendarService')
    def test_register_payment(self, MockCalendar, MockRepo):
        repo_instance = MockRepo.return_value
        register_payment("123", 500, "2026-09-04")
        repo_instance.insert_movimiento_diario.assert_called_once()
        MockCalendar.mark_event_completed.assert_called_once()

    @patch('src.logic.financiero.SheetsRepository')
    @patch('src.logic.financiero.DriveService')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_execute_monthly_closing(self, mock_open, MockDrive, MockRepo):
        repo_instance = MockRepo.return_value
        
        # Test case 1: Positive liquidation, previous closing exists
        repo_instance.get_movimientos_mes.return_value = [
            {"Tipo_Movimiento": "Ingreso", "Monto_Total": 1000, "Monto_IVA": 100, "Clasificacion_IVA": "Débito Fiscal"},
            {"Tipo_Movimiento": "Egreso", "Monto_Total": 200, "Monto_IVA": 20, "Clasificacion_IVA": "Crédito Fiscal"}
        ]
        repo_instance.get_last_cierre_mensual.return_value = {"Saldo_Acumulado_Actual": 500}
        MockDrive.upload_backup.return_value = "mock_drive_id"
        
        drive_id = execute_monthly_closing(9, 2026)
        self.assertEqual(drive_id, "mock_drive_id")
        
        repo_instance.insert_cierre_mensual.assert_called_once_with({
            "Mes_Anio": "09-2026",
            "Total_Ingresos_Efectivo": 1000,
            "Total_Egresos_Efectivo": 200,
            "IVA_Debito_Fiscal": 100,
            "IVA_Credito_Fiscal": 20,
            "Liquidacion_IVA": 80,
            "Estado_IVA": "A Pagar",
            "Margen_Libre_Disponible": 720,
            "Saldo_Acumulado_Actual": 1220
        })
        repo_instance.insert_cierre_mensual.reset_mock()
        
        import tempfile
        expected_path = os.path.join(tempfile.gettempdir(), "backup_2026_9.csv")
        mock_open.assert_called_with(expected_path, "w", newline='', encoding='utf-8')

        # Test case 2: Negative liquidation (Saldo a Favor), first period (no previous closing)
        repo_instance.get_movimientos_mes.return_value = [
            {"Tipo_Movimiento": "Ingreso", "Monto_Total": 500, "Monto_IVA": 50, "Clasificacion_IVA": "Débito Fiscal"},
            {"Tipo_Movimiento": "Egreso", "Monto_Total": 800, "Monto_IVA": 80, "Clasificacion_IVA": "Crédito Fiscal"}
        ]
        repo_instance.get_last_cierre_mensual.return_value = {}
        
        execute_monthly_closing(10, 2026)
        
        repo_instance.insert_cierre_mensual.assert_called_once_with({
            "Mes_Anio": "10-2026",
            "Total_Ingresos_Efectivo": 500,
            "Total_Egresos_Efectivo": 800,
            "IVA_Debito_Fiscal": 50,
            "IVA_Credito_Fiscal": 80,
            "Liquidacion_IVA": -30,
            "Estado_IVA": "Saldo a Favor",
            "Margen_Libre_Disponible": -300,
            "Saldo_Acumulado_Actual": -300
        })

    @patch('src.logic.financiero.SheetsRepository')
    def test_simulate_project(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_presupuesto_base.return_value = {"ingresos": 5000}
        repo_instance.get_obligaciones_activas.return_value = []
        
        project_id = simulate_project(1000, 12, "Auto")
        self.assertIsNotNone(project_id)
        repo_instance.insert_obligacion.assert_called_once()

    @patch('src.logic.financiero.SheetsRepository')
    def test_approve_project(self, MockRepo):
        repo_instance = MockRepo.return_value
        approve_project("789")
        repo_instance.update_obligacion_estado.assert_called_once_with("789", "Activo")

if __name__ == '__main__':
    unittest.main()
