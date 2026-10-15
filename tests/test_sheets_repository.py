import unittest
from repositories.sheets_repository import SheetsRepository
import unittest.mock


class TestSheetsRepository(unittest.TestCase):
    def setUp(self):
        self.repo = SheetsRepository()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_insert_obligacion(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws

        # Test that the mapping returns 15 columns
        self.repo.insert_obligacion({"ID_Obligacion": "123"})
        mock_ws.append_row.assert_called_once()
        called_args = mock_ws.append_row.call_args[0][0]
        self.assertEqual(len(called_args), 15)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_update_obligacion_estado(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"ID_Obligacion": "123", "Estado": "Simulado"}
        ]
        mock_get_sheet.return_value = mock_ws
        self.repo.update_obligacion_estado("123", "Activo")
        mock_ws.update_cell.assert_called_once()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_obligacion_by_id(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"ID_Obligacion": "123"}]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.get_obligacion_by_id("123")
        self.assertEqual(res, {"ID_Obligacion": "123"})

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_obligaciones_activas(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"ID_Obligacion": "123", "Estado": "Activo"},
            {"ID_Obligacion": "456", "Estado": "Simulado"},
        ]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_obligaciones_activas()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ID_Obligacion"], "123")

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_update_obligacion_saldo(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "ID_Obligacion": "123",
                "Saldo_Actual": 1000,
                "Cuotas_Restantes": 5,
                "Estado": "Activo",
            }
        ]
        mock_get_sheet.return_value = mock_ws

        self.repo.update_obligacion_saldo(
            "123", 500, cuotas_restantes=4, nuevo_estado="Pagado"
        )

        self.assertEqual(mock_ws.update_cell.call_count, 3)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_insert_movimiento_diario(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws
        self.repo.insert_movimiento_diario({"Monto_Total": 100})
        mock_ws.append_row.assert_called_once()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_movimientos_mes(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"Fecha": "15/05/2023", "Mes": "05/2023"}
        ]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_movimientos_mes("5", "2023")
        self.assertEqual(len(result), 1)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_insert_cierre_mensual(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws
        self.repo.insert_cierre_mensual({"Total_Ingresos_Efectivo": 2000})
        mock_ws.append_row.assert_called_once()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_last_cierre_mensual(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"Saldo_Acumulado_Actual": 100},
            {"Saldo_Acumulado_Actual": 300},
        ]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.get_last_cierre_mensual()
        self.assertEqual(res["Saldo_Acumulado_Actual"], 300)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_presupuesto_base(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [{"Tipo_Flujo": "Ingreso"}]
        mock_get_sheet.return_value = mock_ws
        result = self.repo.get_presupuesto_base()
        self.assertTrue(isinstance(result, dict))

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_obtener_presupuesto_base_completo(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"Tipo_Flujo": "Ingreso", "Monto_Mensual_Gs": 5000},
            {"Tipo_Flujo": "Egreso", "Monto_Mensual_Gs": 2000},
            {"Tipo_Ingreso_Gasto": "Gasto", "Monto_Mensual_Gs": 1000},
        ]
        mock_get_sheet.return_value = mock_ws
        ingresos, gastos = self.repo.obtener_presupuesto_base_completo()
        self.assertEqual(ingresos, 5000)
        self.assertEqual(gastos, 3000)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_records_header_normalization_cuotas(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        # Simulate remote sheet having 'Tasa Interés' column instead of 'Cuotas'
        mock_ws.get_all_records.side_effect = [
            Exception("Header mismatch"),
            [
                {
                    "ID_Obligacion": "OBL-10",
                    "Nombre": "Préstamo Cooperativa",
                    "Tasa Interés": 12,
                    "Estado": "Activo",
                }
            ],
        ]
        mock_get_sheet.return_value = mock_ws
        activas = self.repo.get_obligaciones_activas()
        self.assertEqual(len(activas), 1)
        self.assertEqual(activas[0]["Cuotas"], 12)
        self.assertEqual(activas[0]["Tasa_Interes"], 12)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_obtener_ultimo_salario_libro_diario(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "Movimiento": "Ingreso",
                "Categoría": "Salario",
                "Proveedor/Cliente": "Empresa ABC",
                "Total": 4500000,
            },
            {
                "Movimiento": "Egreso",
                "Categoría": "Supermercado",
                "Proveedor/Cliente": "Super X",
                "Total": 300000,
            },
            {
                "Movimiento": "Ingreso",
                "Categoría": "Sueldo",
                "Proveedor/Cliente": "Empresa ABC",
                "Total": 5200000,
            },
        ]
        mock_get_sheet.return_value = mock_ws
        salario = self.repo.obtener_ultimo_salario_libro_diario()
        # Debe tomar el más reciente (5.200.000)
        self.assertEqual(salario, 5200000)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_obtener_ultimo_salario_libro_diario_none_found(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "Movimiento": "Egreso",
                "Categoría": "Supermercado",
                "Proveedor/Cliente": "Super X",
                "Total": 300000,
            }
        ]
        mock_get_sheet.return_value = mock_ws
        salario = self.repo.obtener_ultimo_salario_libro_diario()
        self.assertEqual(salario, 0)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_upsert_salario_presupuesto_base_update_existing(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "Tipo_Flujo": "Ingreso Fijo",
                "Categoria": "Salario",
                "Concepto": "Sueldo",
                "Monto_Mensual_Gs": 4000000,
                "Tipo_Ingreso_Gasto": "Fijo",
                "Observaciones": "",
            }
        ]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.upsert_salario_presupuesto_base(5500000)
        self.assertTrue(res)
        mock_ws.update_cell.assert_called_once_with(2, 4, 5500000)
        mock_ws.append_row.assert_not_called()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_upsert_salario_presupuesto_base_insert_new(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "Tipo_Flujo": "Gasto Fijo",
                "Categoria": "Alquiler",
                "Concepto": "Vivienda",
                "Monto_Mensual_Gs": 2000000,
                "Tipo_Ingreso_Gasto": "Fijo",
                "Observaciones": "",
            }
        ]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.upsert_salario_presupuesto_base(6000000)
        self.assertTrue(res)
        mock_ws.update_cell.assert_not_called()
        mock_ws.append_row.assert_called_once_with(
            [
                "Ingreso Fijo",
                "Salario",
                "Sueldo Mensual",
                6000000,
                "Fijo",
                "Auto-sincronizado desde Libro Diario",
            ]
        )

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_upsert_salario_presupuesto_base_invalid_amount(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws
        res = self.repo.upsert_salario_presupuesto_base(0)
        self.assertFalse(res)
        mock_ws.update_cell.assert_not_called()
        mock_ws.append_row.assert_not_called()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_insert_movimiento_diario_auto_sync_salario(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws

        with unittest.mock.patch.object(
            self.repo, "upsert_salario_presupuesto_base"
        ) as mock_upsert:
            movimiento = {
                "Fecha": "15/10/2026",
                "Movimiento": "Ingreso",
                "Categoría": "Sueldo",
                "Total": 4800000,
            }
            self.repo.insert_movimiento_diario(movimiento)
            mock_ws.append_row.assert_called_once()
            mock_upsert.assert_called_once_with(4800000)


if __name__ == "__main__":
    unittest.main()
