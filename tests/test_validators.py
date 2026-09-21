import pytest
from com.utils.validators import (
    parse_monto,
    parse_cuotas,
    validate_fecha,
    validate_categoria,
)


def test_parse_monto_valid():
    assert parse_monto(50000) == 50000
    assert parse_monto("50000") == 50000
    assert parse_monto("50.000") == 50000
    assert parse_monto("50,000") == 50000
    assert parse_monto("Gs. 50.000") == 50000
    assert parse_monto(" 1500000 ") == 1500000
    assert parse_monto(100.0) == 100


def test_parse_monto_invalid():
    with pytest.raises(ValueError):
        parse_monto(0)
    with pytest.raises(ValueError):
        parse_monto(-500)
    with pytest.raises(ValueError):
        parse_monto("abc")
    with pytest.raises(ValueError):
        parse_monto(None)
    with pytest.raises(ValueError):
        parse_monto("")


def test_parse_cuotas_valid():
    assert parse_cuotas(1) == 1
    assert parse_cuotas("12") == 12
    assert parse_cuotas(" 24 ") == 24


def test_parse_cuotas_invalid():
    with pytest.raises(ValueError):
        parse_cuotas(0)
    with pytest.raises(ValueError):
        parse_cuotas(-5)
    with pytest.raises(ValueError):
        parse_cuotas("tres")
    with pytest.raises(ValueError):
        parse_cuotas(None)


def test_validate_fecha_valid():
    assert validate_fecha("21/09/2026") == "21/09/2026"
    assert validate_fecha("01/01/2025") == "01/01/2025"


def test_validate_fecha_invalid():
    with pytest.raises(ValueError):
        validate_fecha("2026-09-21")
    with pytest.raises(ValueError):
        validate_fecha("31/02/2026")
    with pytest.raises(ValueError):
        validate_fecha("invalida")
    with pytest.raises(ValueError):
        validate_fecha("")


def test_validate_categoria_valid():
    cats = ["Alimentación", "Transporte", "Hogar", "Salud"]
    assert validate_categoria("alimentación", cats) == "Alimentación"
    assert validate_categoria("TRANSPORTE", cats) == "Transporte"
    assert validate_categoria("Hogar", cats) == "Hogar"


def test_validate_categoria_invalid():
    cats = ["Alimentación", "Transporte"]
    with pytest.raises(ValueError):
        validate_categoria("Criptomonedas", cats)
    with pytest.raises(ValueError):
        validate_categoria("", cats)
