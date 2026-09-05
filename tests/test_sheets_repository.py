import unittest
from repositories.sheets_repository import SheetsRepository
import unittest.mock

class TestSheetsRepository(unittest.TestCase):
    def setUp(self):
        self.repo = SheetsRepository()

    def test_insert_obligacion(self):
        self.repo.insert_obligacion({"ID_Obligacion": "123"})

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_update_obligacion_estado(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"ID_Obligacion": "123", "Estado": "Simulado"}]
        mock_get_sheet.return_value = mock_ws
        self.repo.update_obligacion_estado("123", "Activo")
        mock_ws.update_cell.assert_called_once()

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_obligacion_by_id(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"ID_Obligacion": "123"}]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.get_obligacion_by_id("123")
        self.assertEqual(res, {"ID_Obligacion": "123"})

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_obligaciones_activas(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"ID_Obligacion": "123", "Estado": "Activo"}, {"ID_Obligacion": "456", "Estado": "Simulado"}]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_obligaciones_activas()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ID_Obligacion"], "123")

    def test_insert_movimiento_diario(self):
        self.repo.insert_movimiento_diario({"Monto_Total": 100})

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_movimientos_mes(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"Fecha": "2023-05-15"}]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_movimientos_mes("5", "2023")
        self.assertEqual(len(result), 1)

    def test_insert_cierre_mensual(self):
        self.repo.insert_cierre_mensual({"Total_Ingresos_Efectivo": 2000})

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_last_cierre_mensual(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"Saldo_Acumulado_Actual": 100}, {"Saldo_Acumulado_Actual": 300}]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.get_last_cierre_mensual()
        self.assertEqual(res["Saldo_Acumulado_Actual"], 300)

    def test_get_presupuesto_base(self):
        result = self.repo.get_presupuesto_base()
        self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main()
