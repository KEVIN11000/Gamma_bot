import os
import sys
from unittest.mock import MagicMock
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

from migrar_obligaciones_maestro import (
    realinear_fila_obligacion,
    migrar_hoja_obligaciones_maestro,
)


def test_realinear_fila_vacia():
    fila, modificada = realinear_fila_obligacion([])
    assert fila == []
    assert modificada is False

    fila2, mod2 = realinear_fila_obligacion(["", "", ""])
    assert mod2 is False


def test_realinear_fila_15_columnas_legacy():
    # Estructura legacy (15 cols): ID, Nombre, Entidad, Monto_Inicial, Saldo_Actual, Estado, ...
    legacy_row = [
        "OBL-001",
        "Préstamo Personal",
        "Banco Itaú",
        "10000000",
        "8000000",
        "Activo",
        "500000",
        "2026-01-01",
        "Obs",
        "12",
        "evt_123",
        "5",
        "24",
        "16",
        "1",
    ]
    assert len(legacy_row) == 15

    alineada, modificada = realinear_fila_obligacion(legacy_row)
    assert modificada is True
    assert len(alineada) == 16
    assert alineada[0] == "OBL-001"
    assert alineada[1] == "Deuda"  # Tipo insertado en columna B
    assert alineada[2] == "Préstamo Personal"  # Nombre en col C
    assert alineada[3] == "Banco Itaú"  # Entidad en col D
    assert alineada[4] == "10000000"  # Monto_Inicial en col E
    assert alineada[5] == "8000000"  # Saldo_Actual en col F
    assert alineada[6] == "Activo"  # Estado en col G
    assert alineada[7] == "500000"  # Cuota_Referencia_Gs en col H


def test_realinear_fila_16_columnas_con_desfasaje():
    # Caso empírico de Módulo 5: la fila tiene 16 celdas pero los datos están corridos
    # col 1: Nombre, col 2: Entidad, col 3: Monto, col 4: Saldo, col 5: Estado ("Activo")
    row_desfasada = [
        "OBL-002",
        "Alquiler Casa",
        "Inmobiliaria",
        "1500000",
        "1500000",
        "Activo",
        "1500000",
        "2026-01-01",
        "Contrato",
        "12",
        "",
        "10",
        "12",
        "6",
        "2",
        "",
    ]
    assert len(row_desfasada) == 16

    alineada, modificada = realinear_fila_obligacion(row_desfasada)
    assert modificada is True
    assert len(alineada) == 16
    assert alineada[0] == "OBL-002"
    assert alineada[1] == "Deuda"
    assert alineada[2] == "Alquiler Casa"
    assert alineada[3] == "Inmobiliaria"
    assert alineada[4] == "1500000"
    assert alineada[5] == "1500000"
    assert alineada[6] == "Activo"
    assert alineada[7] == "1500000"


def test_realinear_fila_ya_alineada():
    # Fila que ya posee Tipo en col 1 y Estado en col 6
    row_ok = [
        "OBL-003",
        "Deuda",
        "Tarjeta Crédito",
        "Banco Atlas",
        "5000000",
        "2000000",
        "Activo",
        "300000",
        "2026-01-01",
        "Pago puntual",
        "0",
        "",
        "15",
        "0",
        "0",
        "3",
    ]
    alineada, modificada = realinear_fila_obligacion(row_ok)
    assert modificada is False
    assert alineada == row_ok


def test_migrar_hoja_dry_run_y_apply():
    mock_ws = MagicMock()
    # Encabezado + 1 fila desfasada (15 cols) + 1 fila ok (16 cols)
    mock_ws.get_all_values.return_value = [
        [
            "ID_Obligacion",
            "Tipo",
            "Nombre",
            "Entidad",
            "Monto_Inicial",
            "Saldo_Actual",
            "Estado",
        ],
        [
            "OBL-1",
            "Alquiler",
            "Inmo",
            "1500000",
            "1500000",
            "Activo",
            "1500000",
            "2026-01-01",
            "Contrato",
            "12",
            "",
            "10",
            "12",
            "6",
            "2",
        ],
        [
            "OBL-2",
            "Deuda",
            "Prestamo",
            "Banco",
            "1000",
            "500",
            "Activo",
            "100",
            "2026-01-01",
            "Obs",
            "1",
            "",
            "10",
            "1",
            "1",
            "1",
        ],
    ]

    # 1. En dry-run=True, no llama a ws.update
    res_dry = migrar_hoja_obligaciones_maestro(ws=mock_ws, dry_run=True)
    assert res_dry["dry_run"] is True
    assert res_dry["filas_migradas"] == 1
    mock_ws.update.assert_not_called()

    # 2. En dry-run=False, debe llamar a ws.update
    res_apply = migrar_hoja_obligaciones_maestro(ws=mock_ws, dry_run=False)
    assert res_apply["dry_run"] is False
    assert res_apply["filas_migradas"] == 1
    mock_ws.update.assert_called_once()
