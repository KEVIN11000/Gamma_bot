import unittest
import os
from unittest.mock import patch

# Ensure we don't write to /tmp on Windows during tests, but our code hardcodes /tmp,
# so we mock open or just let it fail/write to the C: drive if it can. 
# Better to mock open.
from logic.financiero import (
    create_debt,
    get_active_debts,
    register_payment,
    execute_monthly_closing,
    simulate_project,
    approve_project
)

class TestFinancieroLogic(unittest.TestCase):

    @patch('logic.financiero.SheetsRepository')
    @patch('logic.financiero.CalendarService')
    def test_create_debt(self, MockCalendar, MockRepo):
        repo_instance = MockRepo.return_value
        debt_id = create_debt("Banco X", "Prestamo", 10000, 12, "2026-10-01")
        self.assertIsNotNone(debt_id)
        repo_instance.insert_deuda.assert_called_once()
        MockCalendar.create_event.assert_called_once()

    @patch('logic.financiero.SheetsRepository')
    def test_get_active_debts(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_deudas_activas.return_value = [{"id_deuda": "123", "estado": "activa"}]
        
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
        register_payment("123", 500, "2026-09-04")
        repo_instance.insert_pago_abono.assert_called_once()
        repo_instance.insert_movimiento_diario.assert_called_once()
        MockCalendar.mark_event_completed.assert_called_once()

    @patch('logic.financiero.SheetsRepository')
    @patch('logic.financiero.DriveService')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_execute_monthly_closing(self, mock_open, MockDrive, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_movimientos_mes.return_value = [
            {"tipo_movimiento": "Ingreso", "total": 1000},
            {"tipo_movimiento": "Gasto", "total": 200}
        ]
        MockDrive.upload_backup.return_value = "mock_drive_id"
        
        drive_id = execute_monthly_closing(9, 2026)
        self.assertEqual(drive_id, "mock_drive_id")
        import tempfile
        expected_path = os.path.join(tempfile.gettempdir(), "backup_2026_9.csv")
        mock_open.assert_called_once_with(expected_path, "w")

    @patch('logic.financiero.SheetsRepository')
    def test_simulate_project(self, MockRepo):
        repo_instance = MockRepo.return_value
        repo_instance.get_presupuesto_base.return_value = {"mld": 5000}
        
        project_id = simulate_project(1000, 12, "Auto")
        self.assertIsNotNone(project_id)
        repo_instance.insert_simulacion.assert_called_once()

    @patch('logic.financiero.SheetsRepository')
    def test_approve_project(self, MockRepo):
        repo_instance = MockRepo.return_value
        approve_project("789")
        repo_instance.update_simulacion_estado.assert_called_once_with("789", "aprobado")

if __name__ == '__main__':
    unittest.main()
