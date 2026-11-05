import pytest
from pydantic import ValidationError

from api.schemas import (
    GastoFijoItem,
    PresupuestoFijosResponse,
    GastoFijoUpdate,
    GastoFijoCreate,
    SalarioBaseUpdate,
    TechoPresupuestarioItem,
    ProyectoSimularRequest,
    ProyectoSimularResponse,
    ProyectoAprobarResponse,
    EstadoJornadaHoyResponse,
    BootstrapResponse,
)


def test_gasto_fijo_item_valido():
    item = GastoFijoItem(concepto="Alquiler", monto=1500000, concepto_id="Alquiler")
    assert item.concepto == "Alquiler"
    assert item.monto == 1500000
    assert item.concepto_id == "Alquiler"


def test_gasto_fijo_item_invalido():
    with pytest.raises(ValidationError):
        GastoFijoItem(concepto="", monto=-10, concepto_id="id")


def test_presupuesto_fijos_response():
    resp = PresupuestoFijosResponse(
        salario_base=6500000,
        total_gastos_fijos=2850000,
        categorias={
            "Vivienda": [
                GastoFijoItem(
                    concepto="Alquiler", monto=1500000, concepto_id="Alquiler"
                )
            ]
        },
    )
    assert resp.salario_base == 6500000
    assert resp.total_gastos_fijos == 2850000
    assert "Vivienda" in resp.categorias
    assert len(resp.categorias["Vivienda"]) == 1


def test_gasto_fijo_mutations_validation():
    # Update
    up = GastoFijoUpdate(nuevo_monto=1600000)
    assert up.nuevo_monto == 1600000

    with pytest.raises(ValidationError):
        GastoFijoUpdate(nuevo_monto=0)

    # Create
    cr = GastoFijoCreate(categoria="Servicios", concepto="Internet", monto=180000)
    assert cr.categoria == "Servicios"
    assert cr.concepto == "Internet"
    assert cr.monto == 180000

    with pytest.raises(ValidationError):
        GastoFijoCreate(categoria="", concepto="", monto=0)

    # Salario base
    sb = SalarioBaseUpdate(nuevo_salario=7000000)
    assert sb.nuevo_salario == 7000000

    with pytest.raises(ValidationError):
        SalarioBaseUpdate(nuevo_salario=-500)


def test_techo_presupuestario_item():
    techo = TechoPresupuestarioItem(
        categoria="Supermercado",
        limite_mensual=1200000,
        consumido=980000,
        porcentaje=81.6,
        umbral_alerta=80,
        alerta_emitida=True,
        estado="ALERTA",
        mensaje="Consumido 81.6%",
    )
    assert techo.alerta_emitida is True
    assert techo.porcentaje == 81.6
    assert techo.estado == "ALERTA"


def test_proyecto_simular_and_aprobar():
    # Simular Request
    req = ProyectoSimularRequest(concepto="Notebook", monto=6000000, meses=12)
    assert req.monto == 6000000
    assert req.meses == 12

    with pytest.raises(ValidationError):
        ProyectoSimularRequest(concepto="X", monto=0, meses=12)

    with pytest.raises(ValidationError):
        ProyectoSimularRequest(concepto="X", monto=100, meses=0)

    # Simular Response
    sim_resp = ProyectoSimularResponse(
        id_proyecto="PRY-1234",
        concepto="Notebook",
        monto_total=6000000,
        meses=12,
        cuota_mensual=500000,
        ingreso_base=6500000,
        gastos_fijos=2850000,
        cuotas_actuales=1100000,
        margen_libre_post_proyecto=2050000,
        dti_resultante=24.6,
        diagnostico="Viable",
        semaforo="VERDE",
        mensaje="Saludable",
    )
    assert sim_resp.id_proyecto == "PRY-1234"
    assert sim_resp.cuota_mensual == 500000

    # Aprobar Response
    ap_resp = ProyectoAprobarResponse(id_proyecto="PRY-1234")
    assert ap_resp.status == "ok"
    assert ap_resp.id_proyecto == "PRY-1234"
    assert ap_resp.estado == "Activo"


def test_estado_jornada_hoy_response():
    jornada = EstadoJornadaHoyResponse(
        fecha="04/11/2026",
        estado="TRABAJANDO",
        hora_entrada="08:02",
        minutos_transcurridos=195,
        tiempo_transcurrido_formato="3h 15m",
        puede_marcar_entrada=False,
        puede_marcar_salida=True,
    )
    assert jornada.fecha == "04/11/2026"
    assert jornada.estado == "TRABAJANDO"
    assert jornada.puede_marcar_salida is True
    assert jornada.minutos_transcurridos == 195


def test_bootstrap_response():
    jornada = EstadoJornadaHoyResponse(
        fecha="04/11/2026",
        estado="TRABAJANDO",
        hora_entrada="08:02",
        minutos_transcurridos=195,
        tiempo_transcurrido_formato="3h 15m",
        puede_marcar_entrada=False,
        puede_marcar_salida=True,
    )
    boot = BootstrapResponse(
        resumen_financiero={
            "margen_libre": 2500000,
            "saldo_acumulado": 1431300,
            "posicion_iva": 125000,
            "es_debito_fiscal": False,
        },
        estado_asistencia_hoy=jornada,
        clima={
            "temperatura": 24.5,
            "llevar_paraguas": True,
            "condicion": "Lluvia",
        },
        proximos_avisos=[],
        proximos_vencimientos=[],
    )
    assert boot.resumen_financiero["margen_libre"] == 2500000
    assert boot.estado_asistencia_hoy.estado == "TRABAJANDO"
    assert boot.clima["llevar_paraguas"] is True
