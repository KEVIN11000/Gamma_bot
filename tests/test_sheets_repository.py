import unittest
from repositories.sheets_repository import SheetsRepository

class TestSheetsRepository(unittest.TestCase):
    def setUp(self):
        self.repo = SheetsRepository()

    def test_insert_deuda(self):
        self.repo.insert_deuda({"monto": 1000})

    def test_get_deudas_activas(self):
        result = self.repo.get_deudas_activas()
        self.assertEqual(result, [])

    def test_insert_pago_abono(self):
        self.repo.insert_pago_abono({"monto": 500})

    def test_insert_movimiento_diario(self):
        self.repo.insert_movimiento_diario({"monto": 100})

    def test_get_movimientos_mes(self):
        result = self.repo.get_movimientos_mes(5, 2023)
        self.assertEqual(result, [])

    def test_insert_cierre_mensual(self):
        self.repo.insert_cierre_mensual({"total": 2000})

    def test_get_presupuesto_base(self):
        result = self.repo.get_presupuesto_base()
        self.assertEqual(result, {})

    def test_insert_simulacion(self):
        self.repo.insert_simulacion({"proyecto": "A"})

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_update_simulacion_estado(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"id_proyecto": "123", "estado": "pendiente"}]
        mock_get_sheet.return_value = mock_ws
        self.repo.update_simulacion_estado("123", "aprobado")
        mock_ws.update_cell.assert_called_once()

if __name__ == '__main__':
    unittest.main()
