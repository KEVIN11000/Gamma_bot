from api.schemas import ObligacionCreate, ObligacionUpdate, ObligacionResponse
from logic.constants import ENCABEZADOS_OBLIGACIONES_MAESTRO


def test_encabezados_contiene_es_gasto_fijo():
    assert "Es_Gasto_Fijo" in ENCABEZADOS_OBLIGACIONES_MAESTRO
    assert ENCABEZADOS_OBLIGACIONES_MAESTRO[-1] == "Es_Gasto_Fijo"


def test_obligacion_create_default_gasto_fijo():
    obl = ObligacionCreate(
        nombre="Préstamo Vehicular",
        monto_inicial=50000000,
        cuota_referencia_gs=1500000,
    )
    assert obl.es_gasto_fijo is True


def test_obligacion_create_gasto_fijo_explicit_false():
    obl = ObligacionCreate(
        nombre="Deuda Menor Familiar",
        monto_inicial=500000,
        cuota_referencia_gs=100000,
        es_gasto_fijo=False,
    )
    assert obl.es_gasto_fijo is False


def test_obligacion_update_es_gasto_fijo():
    up_none = ObligacionUpdate()
    assert up_none.es_gasto_fijo is None

    up_false = ObligacionUpdate(es_gasto_fijo=False, estado="Pausado")
    assert up_false.es_gasto_fijo is False
    assert up_false.estado == "Pausado"

    up_true = ObligacionUpdate(es_gasto_fijo=True)
    assert up_true.es_gasto_fijo is True


def test_obligacion_response_serialization():
    resp = ObligacionResponse(
        id_obligacion="OBL-1234",
        tipo="Préstamo",
        nombre="Notebook Trabajo",
        entidad="Banco Familiar",
        monto_inicial=6000000,
        saldo_actual=4500000,
        estado="Activo",
        cuota_referencia_gs=500000,
        es_gasto_fijo=True,
    )
    data = resp.model_dump()
    assert data["id_obligacion"] == "OBL-1234"
    assert data["es_gasto_fijo"] is True
