"""Tests unitarios para ExcelReportService (generación de planillas .xlsx)."""

import os
from pathlib import Path
import openpyxl
import pytest

from services.excel_service import DatosPlanillaHoras, ExcelReportService


@pytest.fixture
def sample_datos_horas():
    encabezados = [
        "Día",
        "Fecha",
        "Hora entrada",
        "Salgo almuerzo",
        "Vuelta almuerzo",
        "Hora salida",
        "Horas",
    ]
    filas = [
        ["Martes", "29/09/2026", "09:10", "12:47", "13:16", "17:05", 7.43],
        ["Miércoles", "30/09/2026", "", "", "", "", ""],
        ["Jueves", "01/10/2026", "08:30", "12:19", "12:59", "17:05", 7.92],
        ["Lunes", "05/10/2026", "08:50", "12:19", "13:22", "17:05", 7.23],
        ["Martes", "06/10/2026", "08:06", "12:38", "13:08", "17:03", 8.45],
    ]
    return DatosPlanillaHoras(
        periodo="Octubre 2026",
        nombre_titular="Kevin Peralta",
        encabezados=encabezados,
        filas=filas,
        monto_por_hora=14634,
        saldo_anterior=0,
        descuento=0,
    )


def test_generar_excel_sin_ajuste_ni_descuento(sample_datos_horas):
    """Valida la generación de la planilla cuando no hay saldo anterior ni descuento."""
    ruta_xlsx, msg = ExcelReportService.generar_reporte_horas_excel(sample_datos_horas)

    assert ruta_xlsx is not None
    assert Path(ruta_xlsx).exists()
    assert "Planilla Excel generada" in msg

    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb.active
    assert ws.title == "Octubre 2026"

    # 1. Cabecera A1
    assert "REGISTRO DE HORAS DEL MES DE OCTUBRE 2026 - KEVIN PERALTA" in ws["A1"].value

    # 2. Encabezados fila 2
    assert ws["A2"].value == "Día"
    assert ws["G2"].value == "Horas"

    # 3. Filas de datos (filas 3 a 7)
    assert ws["A3"].value == "Martes"
    assert ws["G3"].value == 7.43
    assert ws["G3"].number_format == "0.00"

    # 4. Cuadro Resumen al pie
    # Fila 8: vacía, Fila 9: Resumen | Cantidades
    assert ws["A9"].value == "Resumen"
    assert ws["B9"].value == "Cantidades"

    # Fila 10: mes
    assert ws["A10"].value == "mes"
    assert ws["B10"].value == "=SUM(G3:G7)"

    # Fila 11: hora
    assert ws["A11"].value == "hora"
    assert ws["B11"].value == 14634

    # Fila 12: por Horas
    assert ws["A12"].value == "por Horas"
    assert ws["B12"].value == "=ROUND(B10*B11, 0)"

    # Fila 13: IVA 10%
    assert ws["A13"].value == "IVA 10%"
    assert ws["B13"].value == "=ROUND(B12*0.1, 0)"

    # Fila 14: INCLUIDO
    assert ws["A14"].value == "INCLUIDO"
    assert ws["B14"].value == "=B12+B13"

    # Fila 15: FACTURA (sin fila de SALDO ANTERIOR ni Descuento intermedia)
    assert ws["A15"].value == "FACTURA"
    assert ws["B15"].value == "=B14"

    # Limpieza de archivo temporal
    if Path(ruta_xlsx).exists():
        os.remove(ruta_xlsx)


def test_generar_excel_con_saldo_anterior(sample_datos_horas):
    """Valida la inclusión de la fila SALDO ANTERIOR cuando saldo_anterior > 0."""
    sample_datos_horas.saldo_anterior = 177364
    ruta_xlsx, msg = ExcelReportService.generar_reporte_horas_excel(sample_datos_horas)

    assert ruta_xlsx is not None
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb.active

    # Fila 14: INCLUIDO
    assert ws["A14"].value == "INCLUIDO"

    # Fila 15: SALDO ANTERIOR
    assert ws["A15"].value == "SALDO ANTERIOR"
    assert ws["B15"].value == 177364

    # Fila 16: FACTURA
    assert ws["A16"].value == "FACTURA"
    assert ws["B16"].value == "=B14+B15"

    if Path(ruta_xlsx).exists():
        os.remove(ruta_xlsx)


def test_generar_excel_con_descuento(sample_datos_horas):
    """Valida la inclusión de la fila Descuento con valor negativo cuando descuento > 0."""
    sample_datos_horas.descuento = 50000
    ruta_xlsx, msg = ExcelReportService.generar_reporte_horas_excel(sample_datos_horas)

    assert ruta_xlsx is not None
    wb = openpyxl.load_workbook(ruta_xlsx)
    ws = wb.active

    # Fila 14: INCLUIDO
    assert ws["A14"].value == "INCLUIDO"

    # Fila 15: Descuento
    assert ws["A15"].value == "Descuento"
    assert ws["B15"].value == -50000

    # Fila 16: FACTURA
    assert ws["A16"].value == "FACTURA"
    assert ws["B16"].value == "=B14+B15"

    if Path(ruta_xlsx).exists():
        os.remove(ruta_xlsx)
