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

    def test_update_simulacion_estado(self):
        self.repo.update_simulacion_estado("123", "aprobado")

if __name__ == '__main__':
    unittest.main()
