import unittest
from repositories.sheets_repository import SheetsRepository
import unittest.mock

class TestSheetsRepository(unittest.TestCase):
    def setUp(self):
        self.repo = SheetsRepository()

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_insert_obligacion(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws
        
        # Test that the mapping returns 15 columns
        self.repo.insert_obligacion({"ID_Obligacion": "123"})
        mock_ws.append_row.assert_called_once()
        called_args = mock_ws.append_row.call_args[0][0]
        self.assertEqual(len(called_args), 15)

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
        
    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_update_obligacion_saldo(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"ID_Obligacion": "123", "Saldo_Actual": 1000, "Cuotas_Restantes": 5, "Estado": "Activo"}]
        mock_get_sheet.return_value = mock_ws
        
        self.repo.update_obligacion_saldo("123", 500, cuotas_restantes=4, nuevo_estado="Pagado")
        
        self.assertEqual(mock_ws.update_cell.call_count, 3)

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_insert_movimiento_diario(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws
        self.repo.insert_movimiento_diario({"Monto_Total": 100})
        mock_ws.append_row.assert_called_once()

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_movimientos_mes(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"Fecha": "2023-05-15"}]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_movimientos_mes("5", "2023")
        self.assertEqual(len(result), 1)

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_insert_cierre_mensual(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws
        self.repo.insert_cierre_mensual({"Total_Ingresos_Efectivo": 2000})
        mock_ws.append_row.assert_called_once()

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_last_cierre_mensual(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"Saldo_Acumulado_Actual": 100}, {"Saldo_Acumulado_Actual": 300}]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.get_last_cierre_mensual()
        self.assertEqual(res["Saldo_Acumulado_Actual"], 300)

    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_get_presupuesto_base(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"Tipo_Flujo": "Ingreso"}]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_presupuesto_base()
        self.assertTrue(isinstance(result, dict))
        
    @unittest.mock.patch('repositories.sheets_repository.SheetsRepository._get_sheet')
    def test_obtener_presupuesto_base_completo(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"Tipo_Flujo": "Ingreso", "Monto_Mensual_Gs": 5000},
            {"Tipo_Flujo": "Egreso", "Monto_Mensual_Gs": 2000},
            {"Tipo_Ingreso_Gasto": "Gasto", "Monto_Mensual_Gs": 1000}
        ]
        mock_get_sheet.return_value = mock_ws
        ingresos, gastos = self.repo.obtener_presupuesto_base_completo()
        self.assertEqual(ingresos, 5000)
        self.assertEqual(gastos, 3000)

if __name__ == '__main__':
    unittest.main()
