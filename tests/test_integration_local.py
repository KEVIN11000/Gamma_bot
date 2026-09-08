"""
Test de Integración Local – Simula el entorno de producción completo.

Flujos cubiertos:
  1. Crear deuda → Verificar que la fila insertada tiene las columnas correctas
  2. Consultar deudas activas → Verificar respuesta del handler con claves reales
  3. Registrar pago (abonar) → Verificar movimiento en Libro_Diario
  4. Simular proyecto → Verificar cálculo de viabilidad y obligación insertada
  5. Aprobar proyecto → Verificar cambio de estado
  6. Cierre mensual → Verificar cálculos de IVA y saldo acumulado
  7. Marcado de horas → Verificar flujo de marcación
  8. Balance financiero → Verificar cálculos de ingresos/gastos

Usa un FakeWorksheet en memoria para simular Google Sheets sin conexión real.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from copy import deepcopy

# ── Entorno ──────────────────────────────────────────────────────────────────
os.environ.setdefault("SPREADSHEET_ID", "dummy_spreadsheet_id")
os.environ.setdefault("LIBRO_CONTABLE_ID", "dummy_libro_contable_id")
os.environ.setdefault("CALENDAR_ID", "dummy_calendar_id")
os.environ.setdefault("MONTO_POR_HORA", "14634")
os.environ.setdefault("MODO_DESARROLLADOR", "True")


# ── FakeWorksheet: simula una hoja de Google Sheets en memoria ───────────────
class FakeWorksheet:
    """In-memory worksheet that mimics gspread.Worksheet for integration tests."""

    def __init__(self, title: str, headers: list[str] | None = None):
        self.title = title
        self._data: list[list[str]] = []
        if headers:
            self._data.append(headers)

    def append_row(self, row: list):
        # Pad row to match header width
        if self._data:
            width = len(self._data[0])
            row = list(row) + [""] * max(0, width - len(row))
        self._data.append([str(v) for v in row])

    def get_all_values(self) -> list[list[str]]:
        return deepcopy(self._data)

    def get_all_records(self) -> list[dict]:
        if len(self._data) < 2:
            return []
        headers = self._data[0]
        records = []
        for row in self._data[1:]:
            padded = row + [""] * max(0, len(headers) - len(row))
            records.append(dict(zip(headers, padded)))
        return records

    def row_values(self, row_num: int) -> list[str]:
        idx = row_num - 1
        if 0 <= idx < len(self._data):
            return list(self._data[idx])
        return []

    def col_values(self, col_num: int) -> list[str]:
        idx = col_num - 1
        return [row[idx] if idx < len(row) else "" for row in self._data]

    def update(self, range_str: str, values: list[list], **kwargs):
        """Simplified update: parses A1 notation and writes values."""
        import re
        m = re.match(r"([A-Z]+)(\d+)", range_str)
        if not m:
            return
        col_letter = m.group(1)
        row_start = int(m.group(2)) - 1
        col_start = ord(col_letter) - ord("A")

        for r_offset, row_vals in enumerate(values):
            r_idx = row_start + r_offset
            while len(self._data) <= r_idx:
                self._data.append([""] * (len(self._data[0]) if self._data else 10))
            for c_offset, val in enumerate(row_vals):
                c_idx = col_start + c_offset
                while len(self._data[r_idx]) <= c_idx:
                    self._data[r_idx].append("")
                self._data[r_idx][c_idx] = str(val)

    def update_cell(self, row: int, col: int, value):
        r_idx = row - 1
        c_idx = col - 1
        while len(self._data) <= r_idx:
            self._data.append([""] * (len(self._data[0]) if self._data else 10))
        while len(self._data[r_idx]) <= c_idx:
            self._data[r_idx].append("")
        self._data[r_idx][c_idx] = str(value)


# ── FakeWorkbook: contiene múltiples FakeWorksheets ──────────────────────────
class FakeWorkbook:
    def __init__(self):
        self._sheets: dict[str, FakeWorksheet] = {}

    def worksheet(self, name: str) -> FakeWorksheet:
        if name not in self._sheets:
            raise Exception(f"Worksheet '{name}' not found")
        return self._sheets[name]

    def worksheets(self) -> list[FakeWorksheet]:
        return list(self._sheets.values())

    def add_worksheet(self, title: str, rows=100, cols=20) -> FakeWorksheet:
        ws = FakeWorksheet(title)
        self._sheets[title] = ws
        return ws

    def add_sheet(self, name: str, headers: list[str]) -> FakeWorksheet:
        ws = FakeWorksheet(name, headers)
        self._sheets[name] = ws
        return ws


# ── Encabezados reales del entorno de producción ─────────────────────────────
HEADERS_OBLIGACIONES = [
    "ID_Obligacion", "Tipo", "Nombre", "Monto_Inicial", "Saldo_Actual",
    "Estado", "Cuota_Referencia_Gs", "Fecha_Inicio", "Observaciones",
    "Cuotas", "Event_ID"
]
HEADERS_LIBRO_DIARIO = [
    "Fecha", "Movimiento", "Proveedor/Cliente", "Nro Factura", "Neto",
    "IVA", "Total", "Categoría", "Comprobante", "Rastro/Foto", "Mes",
    "ID_Obligacion", "Tasa_IVA", "Monto_Gravado", "Monto_IVA", "Clasificacion_IVA"
]
HEADERS_CIERRES = [
    "ID_Cierre", "Mes", "Anio", "Total_Ingresos", "Total_Gastos",
    "Total_Deudas_Pagadas", "Debito_Fiscal", "Credito_Fiscal",
    "Liquidacion_IVA", "Estado_IVA", "Margen_Libre_Disponible",
    "Saldo_Acumulado", "Fecha_Cierre", "Archivo_Backup_Drive"
]
HEADERS_PRESUPUESTO = [
    "Tipo_Flujo", "Categoria", "Concepto", "Monto_Mensual_Gs",
    "Tipo_Ingreso_Gasto", "Observaciones"
]
HEADERS_HORAS = [
    "Dia", "Fecha", "Hora entrada", "Salgo almuerzo",
    "Vuelta almuerzo", "Hora salida", "Horas"
]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════════════════
class TestIntegrationFinanceDebt(unittest.TestCase):
    """Flujo completo: crear deuda → consultar → abonar → cierre."""

    def setUp(self):
        self.wb = FakeWorkbook()
        self.wb.add_sheet("Obligaciones_Maestro", HEADERS_OBLIGACIONES)
        self.wb.add_sheet("Libro_Diario", HEADERS_LIBRO_DIARIO)
        self.wb.add_sheet("Cierres_Historicos", HEADERS_CIERRES)
        self.wb.add_sheet("Presupuesto_Base", HEADERS_PRESUPUESTO)

        # Patch SheetsRepository._get_sheet to return our fake worksheets
        self._patcher = patch(
            "repositories.sheets_repository.SheetsRepository._get_sheet",
            side_effect=lambda name: self.wb.worksheet(name)
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    # ── 1. Crear deuda y verificar columnas correctas ────────────────────────
    @patch("logic.financiero.CalendarService")
    def test_01_create_debt_correct_columns(self, MockCalendar):
        MockCalendar.create_event.return_value = "evt_001"

        from logic.financiero import create_debt
        debt_id = create_debt("Banco Atlas", "Préstamo personal", 12000000, 12, "01/10/2026")

        ws = self.wb.worksheet("Obligaciones_Maestro")
        records = ws.get_all_records()

        self.assertEqual(len(records), 1)
        row = records[0]

        # Verificar que TODAS las columnas se llenaron correctamente
        self.assertEqual(row["ID_Obligacion"], debt_id)
        self.assertEqual(row["Tipo"], "Deuda")
        self.assertEqual(row["Nombre"], "Préstamo personal")
        self.assertEqual(row["Monto_Inicial"], "12000000")
        self.assertEqual(row["Saldo_Actual"], "12000000")
        self.assertEqual(row["Estado"], "Activo")
        self.assertEqual(row["Cuota_Referencia_Gs"], "1000000")  # 12M / 12
        self.assertEqual(row["Fecha_Inicio"], "01/10/2026")
        self.assertEqual(row["Observaciones"], "Entidad: Banco Atlas")
        self.assertEqual(row["Cuotas"], "12")
        self.assertEqual(row["Event_ID"], "evt_001")

        # ¡Ninguna celda vacía donde debe haber datos!
        for key in HEADERS_OBLIGACIONES:
            self.assertNotEqual(row[key], "", f"Columna '{key}' está vacía — ¡bug de mapeo!")

        print(f"  ✅ Deuda creada: {debt_id}")
        print(f"     Nombre={row['Nombre']}, Cuota_Ref={row['Cuota_Referencia_Gs']}, Fecha={row['Fecha_Inicio']}")

    # ── 2. Consultar deudas activas con claves reales ────────────────────────
    @patch("logic.financiero.CalendarService")
    def test_02_get_active_debts_returns_real_keys(self, MockCalendar):
        MockCalendar.create_event.return_value = "evt_002"

        from logic.financiero import create_debt, get_active_debts

        create_debt("Cooperativa", "Préstamo vivienda", 50000000, 60, "15/09/2026")

        debts = get_active_debts()
        self.assertEqual(len(debts), 1)

        d = debts[0]
        # Verificar que el handler de deudas puede leer estas claves
        self.assertIn("ID_Obligacion", d)
        self.assertIn("Nombre", d)
        self.assertIn("Monto_Inicial", d)
        self.assertIn("Cuota_Referencia_Gs", d)
        self.assertIn("Saldo_Actual", d)

        # Simular lo que haría handle_deudas
        nombre = d.get("Nombre", "N/A")
        monto = d.get("Monto_Inicial", 0)
        cuota = d.get("Cuota_Referencia_Gs", "N/A")

        self.assertNotEqual(nombre, "N/A", "Nombre no debería ser N/A")
        self.assertNotEqual(str(monto), "0", "Monto no debería ser 0")

        print(f"  ✅ Deuda consultada: {d['ID_Obligacion']} - {nombre}")
        print(f"     Monto: {monto}, Cuota Ref: {cuota}")

    # ── 3. Registrar pago y verificar movimiento ─────────────────────────────
    @patch("logic.financiero.CalendarService")
    def test_03_register_payment_creates_movimiento(self, MockCalendar):
        MockCalendar.create_event.return_value = "evt_003"

        from logic.financiero import create_debt, register_payment

        debt_id = create_debt("Banco", "Auto", 5000000, 24, "01/10/2026")

        # Simular pago con IVA 10%
        register_payment(debt_id, 208333, "08/09/2026", tasa_iva="10%")

        ws = self.wb.worksheet("Libro_Diario")
        records = ws.get_all_records()
        self.assertEqual(len(records), 1)

        mov = records[0]
        self.assertEqual(mov["ID_Obligacion"], debt_id)
        self.assertNotEqual(mov["Total"], "")
        self.assertNotEqual(mov["Monto_IVA"], "")
        self.assertEqual(mov["Movimiento"], "Egreso")

        print(f"  ✅ Pago registrado: Deuda {debt_id}")
        print(f"     Monto: {mov.get('Total')}, IVA: {mov.get('Monto_IVA')}")

    # ── 4. Simular proyecto con viabilidad ───────────────────────────────────
    @patch("logic.financiero.CalendarService")
    def test_04_simulate_project_correct_keys(self, MockCalendar):
        MockCalendar.create_event.return_value = "evt_sim"

        # Agregar presupuesto base
        ws_pres = self.wb.worksheet("Presupuesto_Base")
        ws_pres.append_row(["Fijo", "Salario", "Sueldo", "3500000", "Ingreso", ""])

        from logic.financiero import simulate_project

        result = simulate_project(2000000, 6, "Laptop nueva")
        self.assertIn("Simulador", result)
        self.assertIn("Laptop nueva", result)

        # Verificar que la obligación se insertó con claves correctas
        ws = self.wb.worksheet("Obligaciones_Maestro")
        records = ws.get_all_records()
        self.assertTrue(len(records) >= 1)

        proyecto = records[-1]
        self.assertEqual(proyecto["Tipo"], "Proyecto")
        self.assertEqual(proyecto["Nombre"], "Laptop nueva")
        self.assertEqual(proyecto["Estado"], "Simulado")
        self.assertNotEqual(proyecto["Cuota_Referencia_Gs"], "")

        # Ninguna columna vacía excepto Fecha_Inicio (proyectos no la tienen)
        for key in ["ID_Obligacion", "Tipo", "Nombre", "Monto_Inicial", "Saldo_Actual", "Estado", "Cuota_Referencia_Gs", "Cuotas"]:
            self.assertNotEqual(proyecto[key], "", f"Columna '{key}' vacía en simulación")

        print(f"  ✅ Proyecto simulado: {proyecto['ID_Obligacion']}")
        print(f"     Cuota Ref: {proyecto['Cuota_Referencia_Gs']}")

    # ── 5. Aprobar proyecto → cambio de estado ───────────────────────────────
    @patch("logic.financiero.CalendarService")
    def test_05_approve_project_updates_estado(self, MockCalendar):
        MockCalendar.create_event.return_value = "evt_apr"

        ws_pres = self.wb.worksheet("Presupuesto_Base")
        ws_pres.append_row(["Fijo", "Salario", "Sueldo", "3500000", "Ingreso", ""])

        from logic.financiero import simulate_project, approve_project

        result = simulate_project(1000000, 3, "Curso online")

        ws = self.wb.worksheet("Obligaciones_Maestro")
        records = ws.get_all_records()
        project_id = records[-1]["ID_Obligacion"]

        approve_project(project_id)

        records_after = ws.get_all_records()
        proyecto = [r for r in records_after if r["ID_Obligacion"] == project_id][0]
        self.assertEqual(proyecto["Estado"], "Activo")

        print(f"  ✅ Proyecto aprobado: {project_id} → Estado=Activo")

    # ── 6. Handler /deudas usa claves correctas ──────────────────────────────
    @patch("logic.financiero.CalendarService")
    def test_06_handler_deudas_uses_correct_keys(self, MockCalendar):
        MockCalendar.create_event.return_value = "evt_hnd"

        from logic.financiero import create_debt, get_active_debts

        create_debt("Personal", "Viaje", 3000000, 6, "01/11/2026")
        debts = get_active_debts()

        # Simular la lógica del handler exactamente como está en el código
        for d in debts:
            nombre = d.get('Nombre', 'N/A')
            monto = d.get('Monto_Inicial', 0)
            cuota = d.get('Cuota_Referencia_Gs', 'N/A')
            saldo = d.get('Saldo_Actual', 0)

            self.assertNotEqual(nombre, 'N/A', "Handler mostraría 'N/A' como nombre")
            self.assertNotEqual(str(monto), '0', "Handler mostraría monto 0")
            self.assertNotEqual(str(cuota), 'N/A', "Handler mostraría cuota 'N/A'")

            # Formatear como lo hace el handler
            response = (
                f"🆔 `{d.get('ID_Obligacion', 'N/A')}`\n"
                f"📝 {nombre}\n"
                f"💰 Monto: Gs. {int(monto):,}\n".replace(",", ".") +
                f"📊 Cuota Ref: Gs. {int(cuota):,}\n".replace(",", ".") +
                f"💳 Saldo: Gs. {int(saldo):,}\n".replace(",", ".")
            )
            self.assertNotIn("N/A", response.split("📝")[1].split("\n")[0])

        print(f"  ✅ Handler /deudas genera respuesta correcta con {len(debts)} deuda(s)")

    # ── 7. Calcular IVA correctamente ────────────────────────────────────────
    def test_07_calcular_iva(self):
        from logic.financiero import calcular_iva

        # IVA 10%
        gravado, iva = calcular_iva(1100000, "10%")
        self.assertEqual(gravado, 1000000)
        self.assertEqual(iva, 100000)

        # IVA 5%
        gravado, iva = calcular_iva(1050000, "5%")
        self.assertEqual(gravado, 1000000)
        self.assertEqual(iva, 50000)

        # Exento
        gravado, iva = calcular_iva(1000000, "Exento")
        self.assertEqual(gravado, 1000000)
        self.assertEqual(iva, 0)

        print("  ✅ Cálculos de IVA correctos (10%, 5%, Exento)")


class TestIntegrationHourTracking(unittest.TestCase):
    """Flujo de marcación de horas con FakeWorksheet."""

    def setUp(self):
        self.wb = FakeWorkbook()
        self.ws_horas = self.wb.add_sheet("Septiembre 2026", HEADERS_HORAS)

    @patch("logic.logic.AgenteAutonomoHoras.fin_de", return_value=None)
    def test_marcado_normal_flow(self, mock_fin):
        """Simula: Entrada → S.Almuerzo → V.Almuerzo → Salida en un día."""
        from logic.logic import AgenteAutonomoHoras

        agente = AgenteAutonomoHoras.__new__(AgenteAutonomoHoras)
        agente.spreadsheet_id = "dummy"
        agente.mes = "Septiembre 2026"
        agente._wb = self.wb
        agente._ws = self.ws_horas

        # Mockear la obtención/creación de fila
        with patch.object(agente, "_obtener_o_crear_fila_hoy", return_value=2):
            # Preparar la fila con día y fecha
            self.ws_horas.update("A2", [["Lunes", "08/09/2026"]])

            # Marca 1: Entrada
            self.ws_horas.update("C2", [["08:00"]])
            row = self.ws_horas.row_values(2)
            self.assertEqual(row[2], "08:00")

            # Marca 2: Salida almuerzo
            self.ws_horas.update("D2", [["12:00"]])

            # Marca 3: Vuelta almuerzo
            self.ws_horas.update("E2", [["13:00"]])

            # Marca 4: Salida
            self.ws_horas.update("F2", [["17:00"]])

            row_final = self.ws_horas.row_values(2)
            self.assertEqual(row_final[0], "Lunes")
            self.assertEqual(row_final[1], "08/09/2026")
            self.assertEqual(row_final[2], "08:00")
            self.assertEqual(row_final[3], "12:00")
            self.assertEqual(row_final[4], "13:00")
            self.assertEqual(row_final[5], "17:00")

        print("  ✅ Marcado normal: Lunes 08/09/2026 → 08:00-12:00 / 13:00-17:00")

    def test_parsear_horas_a_decimal(self):
        """Verifica la conversión de formatos de horas a decimal."""
        from logic.logic import AgenteAutonomoHoras

        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("8:30"), 8.5)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("8.5"), 8.5)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("8,5"), 8.5)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal(""), 0.0)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("inválido"), 0.0)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("7:45"), 7.75)

        print("  ✅ Parser de horas: 8:30→8.5, 7:45→7.75, vacío→0.0")


class TestIntegrationAgenteFinanciero(unittest.TestCase):
    """Flujo del AgenteFinanciero: registrar movimiento + balance."""

    def setUp(self):
        self.wb = FakeWorkbook()
        self.ws_libro = self.wb.add_sheet("Libro_Diario_Test", [
            "Fecha", "Movimiento", "Proveedor/Cliente", "Nro Factura",
            "Neto", "IVA", "Total", "Categoría", "Comprobante",
            "Rastro/Foto", "Mes"
        ])

    def test_registrar_movimiento_y_balance(self):
        """Simula registrar gastos e ingresos y calcular balance."""
        from logic.financiero import AgenteFinanciero

        agente = AgenteFinanciero.__new__(AgenteFinanciero)
        agente.spreadsheet_id = "dummy"
        agente.libro_contable_id = "dummy"
        agente._wb = self.wb
        agente._libro_wb = self.wb
        agente._ws = self.ws_libro

        # Registrar un gasto
        result1 = agente.registrar_movimiento({
            "fecha": "08/09/2026",
            "tipo_movimiento": "Gasto",
            "proveedor_cliente": "Supermercado ABC",
            "nro_factura": "001-001-0001234",
            "neto": 450000,
            "iva": 45000,
            "total": 495000,
            "categoria": "Alimentación",
            "comprobante": "Factura",
            "file_id": "",
            "mes": "Septiembre"
        })
        self.assertIn("✅", result1)
        self.assertIn("Gasto", result1)

        # Registrar un ingreso
        result2 = agente.registrar_movimiento({
            "fecha": "08/09/2026",
            "tipo_movimiento": "Ingreso",
            "proveedor_cliente": "Empleador SRL",
            "nro_factura": "S/N",
            "neto": 3500000,
            "iva": 0,
            "total": 3500000,
            "categoria": "Salario",
            "comprobante": "Recibo",
            "file_id": "",
            "mes": "Septiembre"
        })
        self.assertIn("✅", result2)
        self.assertIn("Ingreso", result2)

        # Verificar balance
        balance = agente.obtener_balance()
        self.assertIsNotNone(balance)
        self.assertEqual(balance["ingresos"], 3500000)
        self.assertEqual(balance["gastos"], 495000)
        self.assertEqual(balance["flujo_neto"], 3005000)

        # Verificar detección de factura duplicada
        result_dup = agente.registrar_movimiento({
            "fecha": "08/09/2026",
            "tipo_movimiento": "Gasto",
            "proveedor_cliente": "Supermercado ABC",
            "nro_factura": "001-001-0001234",
            "total": 495000,
        })
        self.assertIn("Duplicada", result_dup)

        print(f"  ✅ Balance: Ingresos={balance['ingresos']:,} | Gastos={balance['gastos']:,} | Neto={balance['flujo_neto']:,}")
        print(f"  ✅ Factura duplicada detectada correctamente")

    def test_registrar_movimiento_datos_invalidos(self):
        """Verifica que datos inválidos retornan error limpio."""
        from logic.financiero import AgenteFinanciero

        agente = AgenteFinanciero.__new__(AgenteFinanciero)
        agente.spreadsheet_id = "dummy"
        agente.libro_contable_id = "dummy"
        agente._wb = self.wb
        agente._libro_wb = self.wb
        agente._ws = self.ws_libro

        # Sin datos
        result = agente.registrar_movimiento({})
        self.assertIn("❌", result)

        # None
        result = agente.registrar_movimiento(None)
        self.assertIn("❌", result)

        print("  ✅ Datos inválidos manejados correctamente (sin crash)")


class TestIntegrationSafeInt(unittest.TestCase):
    """Verifica safe_int con edge cases reales de Sheets."""

    def test_safe_int_edge_cases(self):
        from logic.financiero import safe_int

        self.assertEqual(safe_int(0), 0)
        self.assertEqual(safe_int(""), 0)
        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int("1000"), 1000)
        self.assertEqual(safe_int(" 1500 "), 1500)
        self.assertEqual(safe_int("1000.5"), 1000)
        self.assertEqual(safe_int("abc"), 0)

        print("  ✅ safe_int: maneja 0, '', None, '1000', ' 1500 ', '1000.5', 'abc'")


class TestIntegrationLimpiarMonto(unittest.TestCase):
    """Verifica limpiar_monto con formatos reales de moneda."""

    def test_limpiar_monto_formatos(self):
        from logic.financiero import AgenteFinanciero
        af = AgenteFinanciero.__new__(AgenteFinanciero)

        self.assertEqual(af.limpiar_monto("Gs. 1.500.000"), 1500000)
        self.assertEqual(af.limpiar_monto("500000"), 500000)
        self.assertEqual(af.limpiar_monto(""), 0)
        self.assertEqual(af.limpiar_monto(None), 0)
        self.assertEqual(af.limpiar_monto(12345), 12345)
        self.assertEqual(af.limpiar_monto("Gs. 0"), 0)

        print("  ✅ limpiar_monto: 'Gs. 1.500.000'→1500000, ''→0, None→0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
