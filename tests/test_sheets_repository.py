import unittest
from repositories.sheets_repository import InMemorySheetsCache, SheetsRepository
import unittest.mock


class TestSheetsRepository(unittest.TestCase):
    def setUp(self):
        self.repo = SheetsRepository()
        self.repo.clear_cache()

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_insert_obligacion(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_get_sheet.return_value = mock_ws

        # Test that the mapping returns 16 columns and Entidad is at column D (index 3)
        self.repo.insert_obligacion(
            {"ID_Obligacion": "123", "Entidad": "Banco Familiar"}
        )
        mock_ws.append_row.assert_called_once()
        called_args = mock_ws.append_row.call_args[0][0]
        self.assertEqual(len(called_args), 16)
        self.assertEqual(called_args[3], "Banco Familiar")

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
            {"ID_Obligacion": "789", "Estado": "Pausado"},
            {"ID_Obligacion": "101", "Estado": "Pausada"},
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

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_delete_obligacion(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"ID_Obligacion": "OBL-1", "Estado": "Activo"},
            {"ID_Obligacion": "OBL-2", "Estado": "Simulado"},
        ]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.delete_obligacion("OBL-2")
        self.assertTrue(res)
        mock_ws.delete_rows.assert_called_once_with(3)  # row 3 = header + 2nd item

        # Not found
        res_false = self.repo.delete_obligacion("INEXISTENTE")
        self.assertFalse(res_false)

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_update_obligacion_general(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"ID_Obligacion": "OBL-1", "Estado": "Simulado", "Saldo_Actual": 1000}
        ]
        mock_get_sheet.return_value = mock_ws
        res = self.repo.update_obligacion(
            "OBL-1", {"Estado": "Activo", "Saldo_Actual": 800}
        )
        self.assertTrue(res)
        self.assertEqual(mock_ws.update_cell.call_count, 2)

    def test_in_memory_sheets_cache_lifecycle(self):
        cache = InMemorySheetsCache(default_ttl_seconds=10)
        self.assertIsNone(cache.get("no_existe"))

        cache.set("clave_1", {"dato": 123}, ttl_seconds=5)
        self.assertEqual(cache.get("clave_1"), {"dato": 123})

        # Test expiration
        with unittest.mock.patch("time.time", return_value=1000.0):
            cache.set("clave_temp", "valor", ttl_seconds=2)
        with unittest.mock.patch("time.time", return_value=1003.0):
            self.assertIsNone(cache.get("clave_temp"))

        # Test invalidation by prefix
        cache.set("balance_10_2026", {"ingresos": 100})
        cache.set("balance_11_2026", {"ingresos": 200})
        cache.set("movimientos_todos", [1, 2, 3])

        cache.invalidate("balance_")
        self.assertIsNone(cache.get("balance_10_2026"))
        self.assertIsNone(cache.get("balance_11_2026"))
        self.assertEqual(cache.get("movimientos_todos"), [1, 2, 3])

        cache.clear()
        self.assertIsNone(cache.get("movimientos_todos"))

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_sheets_repository_caching_and_invalidation(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {"Fecha": "01/10/2026", "Movimiento": "Ingreso", "Total": 1000}
        ]
        mock_get_sheet.return_value = mock_ws

        # 1. get_all_movimientos uses cache
        movs1 = self.repo.get_all_movimientos()
        movs2 = self.repo.get_all_movimientos()
        self.assertEqual(movs1, movs2)
        # Should only call _get_sheet once due to caching
        mock_get_sheet.assert_called_once_with("Libro_Diario")

        # 2. insert_movimiento_diario invalidates movimientos_ and balance_
        self.repo.cache.set("balance_10_2026", {"ingresos": 1000})
        self.repo.insert_movimiento_diario(
            {"Fecha": "02/10/2026", "Movimiento": "Egreso"}
        )
        self.assertIsNone(self.repo.cache.get("movimientos_todos"))
        self.assertIsNone(self.repo.cache.get("balance_10_2026"))

        # 3. get_todas_obligaciones uses cache
        mock_ws.get_all_records.return_value = [
            {"ID_Obligacion": "OBL-100", "Estado": "Activo"}
        ]
        mock_get_sheet.reset_mock()
        ob1 = self.repo.get_todas_obligaciones()
        ob2 = self.repo.get_todas_obligaciones()
        self.assertEqual(ob1, ob2)
        mock_get_sheet.assert_called_once_with("Obligaciones_Maestro")

        # 4. mutating obligacion invalidates obligaciones_ and presupuesto_base
        self.repo.cache.set("presupuesto_base", (5000000, 3000000))
        self.repo.insert_obligacion({"ID_Obligacion": "OBL-101"})
        self.assertIsNone(self.repo.cache.get("obligaciones_todas"))
        self.assertIsNone(self.repo.cache.get("presupuesto_base"))

    @unittest.mock.patch("repositories.sheets_repository.SheetsRepository._get_sheet")
    def test_get_todos_cierres_historicos(self, mock_get_sheet):
        mock_ws = unittest.mock.MagicMock()
        mock_ws.get_all_records.return_value = [
            {
                "ID_Cierre": "cierre_01",
                "Mes": "Setiembre",
                "Anio": "2026",
                "Total_Ingresos": 10000000,
                "Total_Gastos": 6000000,
            }
        ]
        mock_get_sheet.return_value = mock_ws

        cierres1 = self.repo.get_todos_cierres_historicos()
        cierres2 = self.repo.get_todos_cierres_historicos()
        self.assertEqual(cierres1, cierres2)
        self.assertEqual(len(cierres1), 1)
        self.assertEqual(cierres1[0]["ID_Cierre"], "cierre_01")
        # Cached: should only call _get_sheet once
        mock_get_sheet.assert_called_once_with("Cierres_Historicos")

        # Invalidate on insert_cierre_mensual
        self.repo.insert_cierre_mensual({"ID_Cierre": "cierre_02"})
        self.assertIsNone(self.repo.cache.get("cierres_historicos"))

    def test_ensure_headers_hoja_vacia(self):
        """Verifica que en una hoja vacía se agregue la fila con encabezados esperados."""
        mock_ws = unittest.mock.MagicMock()
        mock_ws.row_values.return_value = []
        self.repo._ensure_headers(mock_ws, "Obligaciones_Maestro")
        mock_ws.append_row.assert_called_once()
        mock_ws.update_cell.assert_not_called()

    def test_ensure_headers_inconsistencia_estructural_bloquea_sobrescritura(self):
        """Si la fila 1 tiene 15 columnas y hay datos en fila 2, NO debe sobrescribir celdas."""
        mock_ws = unittest.mock.MagicMock()
        # Simular 15 columnas (esquema legacy sin Tipo) y datos en fila 2
        mock_ws.row_values.side_effect = lambda row_idx: (
            ["Col1", "Col2", "Col3"] if row_idx == 1 else ["Val1", "Val2", "Val3"]
        )
        self.repo._ensure_headers(mock_ws, "Obligaciones_Maestro")
        # No debe actualizar celdas para evitar el desfasaje horizontal
        mock_ws.update_cell.assert_not_called()
        mock_ws.append_row.assert_not_called()

    def test_ensure_headers_misma_longitud_actualiza_seguro(self):
        """Si la longitud coincide, se actualizan las celdas de forma segura."""
        mock_ws = unittest.mock.MagicMock()
        from logic.constants import ENCABEZADOS_OBLIGACIONES_MAESTRO

        # Misma cantidad de columnas pero nombres en minúsculas
        legacy_headers = [h.lower() for h in ENCABEZADOS_OBLIGACIONES_MAESTRO]
        mock_ws.row_values.side_effect = lambda row_idx: (
            legacy_headers if row_idx == 1 else ["Val"] * len(legacy_headers)
        )
        self.repo._ensure_headers(mock_ws, "Obligaciones_Maestro")
        self.assertEqual(
            mock_ws.update_cell.call_count, len(ENCABEZADOS_OBLIGACIONES_MAESTRO)
        )


if __name__ == "__main__":
    unittest.main()
