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


def test_aviso_create_and_update_schemas():
    from api.schemas import AvisoCreate, AvisoUpdate

    # Default values
    aviso_default = AvisoCreate(titulo="Dentista", fecha_evento="25/10/2026 15:00")
    assert aviso_default.repeticion == "NINGUNA"
    assert aviso_default.hitos_minutos == [1440]
    assert aviso_default.dias_restantes is None

    # Custom values
    aviso_custom = AvisoCreate(
        titulo="Alquiler",
        fecha_evento="05/11/2026 09:00",
        repeticion="MENSUAL",
        hitos_minutos=[1440, 180, 60],
        dias_restantes=15,
    )
    assert aviso_custom.repeticion == "MENSUAL"
    assert aviso_custom.hitos_minutos == [1440, 180, 60]

    # Update schema
    update_data = AvisoUpdate(titulo="Alquiler Ajustado", repeticion="ANUAL")
    assert update_data.titulo == "Alquiler Ajustado"
    assert update_data.repeticion == "ANUAL"
    assert update_data.fecha_evento is None


def test_obligacion_create_and_update_schemas():
    from api.schemas import ObligacionCreate, ObligacionUpdate

    # Default values
    ob_default = ObligacionCreate(nombre="Préstamo", monto_inicial=5000000)
    assert ob_default.entidad == "General"
    assert ob_default.tipo == "Deuda"
    assert ob_default.estado == "Activo"
    assert ob_default.cuotas_totales == 1
    assert ob_default.cuotas_restantes == 1
    assert ob_default.saldo_actual is None

    # Custom values (Simulada)
    ob_simulada = ObligacionCreate(
        entidad="Banco Itaú",
        nombre="Auto 0km",
        tipo="Préstamo",
        monto_inicial=20000000,
        saldo_actual=20000000,
        cuotas_totales=24,
        cuotas_restantes=24,
        cuota_referencia_gs=950000,
        dia_vencimiento=10,
        estado="Simulado",
        observaciones="En evaluación",
    )
    assert ob_simulada.estado == "Simulado"
    assert ob_simulada.entidad == "Banco Itaú"
    assert ob_simulada.cuota_referencia_gs == 950000

    # Update schema (Aprobar simulación)
    ob_update = ObligacionUpdate(estado="Activo", observaciones="Aprobado")
    assert ob_update.estado == "Activo"
    assert ob_update.monto_inicial is None
