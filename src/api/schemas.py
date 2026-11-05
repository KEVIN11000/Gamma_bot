from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TipoMovimiento(str, Enum):
    INGRESO = "Ingreso"
    GASTO = "Gasto"


class TasaIVA(str, Enum):
    IVA_10 = "10%"
    IVA_5 = "5%"
    EXENTO = "Exento"


class TipoComprobante(str, Enum):
    VIRTUAL_LEGAL = "Virtual Legal"
    FISICA_LEGAL = "Física Legal"
    NO_LEGAL = "No Legal"


class MovimientoCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fecha: Optional[str] = None
    movimiento: TipoMovimiento = Field(
        default=TipoMovimiento.GASTO,
        alias="tipo",
        description="Tipo de movimiento: Gasto o Ingreso",
    )
    proveedor_cliente: str = Field(
        ...,
        alias="concepto",
        description="Proveedor o Cliente / Concepto del movimiento",
    )
    nro_factura: Optional[str] = "S/N"
    total: int = Field(..., gt=0, alias="monto")
    categoria: str = "Varios"
    comprobante: TipoComprobante = TipoComprobante.NO_LEGAL
    tasa_iva: TasaIVA = TasaIVA.IVA_10
    id_obligacion: Optional[str] = None
    rastro_foto: Optional[str] = ""
    client_id: Optional[str] = Field(None, alias="clientId")


class ObligacionCreate(BaseModel):
    entidad: Optional[str] = "General"
    tipo: str = "Deuda"
    nombre: str
    monto_inicial: int = Field(..., gt=0)
    saldo_actual: Optional[int] = None
    cuotas_totales: Optional[int] = 1
    cuotas_restantes: Optional[int] = 1
    cuota_referencia_gs: Optional[int] = 0
    dia_vencimiento: Optional[int] = 0
    fecha_inicio: Optional[str] = None
    estado: str = "Activo"
    observaciones: Optional[str] = ""


class ObligacionUpdate(BaseModel):
    entidad: Optional[str] = None
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    monto_inicial: Optional[int] = None
    saldo_actual: Optional[int] = None
    cuotas_totales: Optional[int] = None
    cuotas_restantes: Optional[int] = None
    cuota_referencia_gs: Optional[int] = None
    dia_vencimiento: Optional[int] = None
    fecha_inicio: Optional[str] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None


class AbonoRequest(BaseModel):
    id_obligacion: str
    monto: int = Field(..., gt=0)
    nro_factura: Optional[str] = "S/N"
    tasa_iva: TasaIVA = TasaIVA.IVA_10


class SimulacionRequest(BaseModel):
    monto: int = Field(..., gt=0)
    meses: int = Field(..., gt=0)
    concepto: Optional[str] = "Simulación General"


class CapacidadPagoRequest(BaseModel):
    deudas_pausadas_simuladas: list[str] = Field(default_factory=list)
    abonos_extraordinarios: dict[str, int] = Field(default_factory=dict)
    ajuste_ingreso_extra: int = 0

    @field_validator("deudas_pausadas_simuladas", mode="before")
    def _val_deudas_pausadas(cls, v: Any) -> list[str]:
        return v if v is not None else []

    @field_validator("abonos_extraordinarios", mode="before")
    def _val_abonos(cls, v: Any) -> dict[str, int]:
        return v if v is not None else {}

    @field_validator("ajuste_ingreso_extra", mode="before")
    def _val_ajuste(cls, v: Any) -> int:
        return v if v is not None else 0


class AvisoCreate(BaseModel):
    titulo: str
    fecha_evento: str  # DD/MM/AAAA HH:MM
    dias_restantes: Optional[int] = None
    repeticion: str = "NINGUNA"
    hitos_minutos: list[int] = Field(default_factory=lambda: [1440])


class AvisoUpdate(BaseModel):
    titulo: Optional[str] = None
    fecha_evento: Optional[str] = None
    dias_restantes: Optional[int] = None
    repeticion: Optional[str] = None
    hitos_minutos: Optional[list[int]] = None


class IAParseRequest(BaseModel):
    texto: str
    tipo: Optional[str] = "Gasto"


class AsistenciaMarcarRequest(BaseModel):
    modo: Optional[str] = "normal"


class AsistenciaMateriaRequest(BaseModel):
    materia: str


class CierreEjecutarRequest(BaseModel):
    hoja: Optional[str] = None
    aplicar_descuento: Optional[bool] = False


class TicketCreate(BaseModel):
    asunto: str
    descripcion: Optional[str] = ""
    origen: Optional[str] = "app"


class TicketUpdate(BaseModel):
    estado: str
    resolucion: Optional[str] = None


class PeriodosResponse(BaseModel):
    periodo_laboral: str
    periodo_contable: str
    sincronizados: bool


class AnaliticasHorasResponse(BaseModel):
    periodo: str
    monto_por_hora: int
    dias_trabajados: int
    total_horas_decimal: float
    total_horas_formato: str
    salario_acumulado_gs: int
    horas_perdidas_decimal: float
    horas_extras_decimal: float
    balance_neto_decimal: float
    horas_perdidas_formato: str
    horas_extras_formato: str
    balance_neto_formato: str
    promedio_horas_por_dia: float


class CuadroResumenHoras(BaseModel):
    mes_horas: float
    hora_tarifa: int
    por_horas: int
    iva_10: int
    incluido: int
    tipo_ajuste: Optional[str] = None
    monto_ajuste: int = 0
    factura_total: int


class ClimaAlertaParaguas(BaseModel):
    necesita_paraguas: bool
    probabilidad_lluvia: int
    motivo: str


class ClimaResponse(BaseModel):
    temperatura_actual: float
    temperatura_min: float
    temperatura_max: float
    condicion: str
    alerta_paraguas: ClimaAlertaParaguas
    actualizado_at: str


class SyncRequest(BaseModel):
    direccion: str = Field(
        "local_to_sheets", pattern="^(local_to_sheets|sheets_to_local)$"
    )
    modulo: str = Field("laboral", pattern="^(laboral|materias|todo)$")
    mes: Optional[int] = None
    anio: Optional[int] = None


class SyncResponse(BaseModel):
    exito: bool
    registros_sincronizados: int
    detalles: str


class WhatsAppMessageData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    remote_jid: str = Field(
        ..., alias="remoteJid", description="ID del chat o número E.164"
    )
    from_me: bool = Field(
        False,
        alias="fromMe",
        description="True si fue enviado por la propia instancia",
    )
    push_name: Optional[str] = Field(
        None, alias="pushName", description="Nombre visible del usuario"
    )
    text: Optional[str] = Field(None, description="Cuerpo del mensaje de texto")
    message_type: str = Field(
        "conversation",
        alias="messageType",
        description="Tipo de mensaje",
    )
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _extract_nested_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        parsed = dict(data)

        # Extract nested key if present (Evolution API structure)
        key = parsed.get("key")
        if isinstance(key, dict):
            if "remote_jid" not in parsed and "remoteJid" not in parsed:
                parsed["remote_jid"] = key.get("remoteJid") or key.get("remote_jid")
            if "from_me" not in parsed and "fromMe" not in parsed:
                parsed["from_me"] = (
                    key.get("fromMe") if "fromMe" in key else key.get("from_me", False)
                )

        # Extract nested message text if present (Evolution API structure)
        msg = parsed.get("message")
        if isinstance(msg, dict) and not parsed.get("text"):
            if "conversation" in msg:
                parsed["text"] = msg["conversation"]
            elif "extendedTextMessage" in msg and isinstance(
                msg["extendedTextMessage"], dict
            ):
                parsed["text"] = msg["extendedTextMessage"].get("text")
            elif "documentMessage" in msg and isinstance(msg["documentMessage"], dict):
                parsed["text"] = msg["documentMessage"].get("caption")

        return parsed


class WhatsAppWebhookEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event: str = Field(
        ...,
        description="Tipo de evento: messages.upsert, send.message, connection.update",
    )
    instance: str = Field(
        "gamma",
        description="Nombre de la instancia que emitió el evento",
    )
    data: WhatsAppMessageData


class WhatsAppWebhookResponse(BaseModel):
    status: str = "ok"
    job_id: Optional[int] = None
    ignored: bool = False
    motivo: Optional[str] = None


class ParseMovementRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    texto: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Texto libre del movimiento financiero a parsear",
    )


class ParsedMovement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    valido: bool = Field(
        ...,
        description="Indica si se extrajo un movimiento con confianza suficiente",
    )
    tipo_movimiento: str = Field(
        default="Gasto",
        description="'Gasto' o 'Ingreso'",
    )
    monto: float = Field(
        default=0.0,
        ge=0.0,
        description="Monto numérico total extraído",
    )
    categoria: str = Field(
        default="Varios",
        description="Categoría normalizada",
    )
    proveedor_cliente: str = Field(
        default="S/N",
        description="Comercio, cliente o proveedor detectado",
    )
    descripcion: str = Field(
        default="",
        description="Descripción limpia del movimiento",
    )
    confianza: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Nivel de certeza de la extracción (0.0 a 1.0)",
    )


class FlujoCajaItemDiario(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fecha: str = Field(..., description="Fecha del día proyectado (YYYY-MM-DD)")
    saldo_inicial: float = Field(..., description="Saldo al comenzar el día")
    ingresos: float = Field(default=0.0, description="Ingresos previstos en el día")
    egresos_fijos: float = Field(
        default=0.0, description="Gastos fijos / cuotas a vencer en el día"
    )
    egresos_variables: float = Field(
        default=0.0, description="Estimación de gasto diario ordinario"
    )
    saldo_final: float = Field(..., description="Saldo al finalizar el día")
    compromisos: list[str] = Field(
        default_factory=list,
        description="Nombres de obligaciones o servicios que vencen",
    )


class FlujoCajaResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saldo_actual: float = Field(
        ..., description="Saldo real actual al inicio del horizonte"
    )
    saldo_proyectado_30d: float = Field(..., description="Saldo esperado al día 30")
    total_ingresos_proyectados: float = Field(
        ..., description="Suma de ingresos esperados en 30 días"
    )
    total_gastos_fijos: float = Field(
        ..., description="Suma de cuotas y servicios fijos a vencer"
    )
    total_gastos_variables_estimados: float = Field(
        ..., description="Suma proyectada de gastos variables"
    )
    dias_criticos: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Días con saldo negativo o por debajo del umbral de reserva",
    )
    dias: list[FlujoCajaItemDiario] = Field(
        default_factory=list, description="Serie temporal de 30 días"
    )


class DispositivoCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_token: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Token push único del dispositivo",
    )
    platform: str = Field(
        default="android",
        pattern="^(android|ios|web)$",
        description="Plataforma del cliente",
    )
    alias_usuario: Optional[str] = Field(default="default", max_length=100)


class DispositivoResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = "ok"
    registrado: bool = True
    dispositivos_activos: int = 1


# ============================================================================
# Schemas v2.0.0: Presupuesto Base, Techos, Proyectos, Asistencia y Bootstrap
# ============================================================================


class GastoFijoItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    concepto: str = Field(
        ..., min_length=1, description="Nombre o concepto del gasto fijo"
    )
    monto: int = Field(..., ge=0, description="Monto mensual en guaraníes")
    concepto_id: str = Field(..., description="Identificador único del concepto")


class PresupuestoFijosResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    salario_base: int = Field(
        ..., ge=0, description="Salario o ingreso base mensual en guaraníes"
    )
    total_gastos_fijos: int = Field(
        ..., ge=0, description="Total acumulado de gastos fijos mensuales"
    )
    categorias: dict[str, list[GastoFijoItem]] = Field(
        default_factory=dict,
        description="Mapa de categoría -> lista de conceptos fijos",
    )


class GastoFijoUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nuevo_monto: int = Field(
        ..., gt=0, description="Nuevo importe mensual del gasto fijo"
    )


class GastoFijoCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    categoria: str = Field(
        ..., min_length=1, description="Categoría (ej. Vivienda, Servicios)"
    )
    concepto: str = Field(..., min_length=1, description="Nombre del concepto fijo")
    monto: int = Field(..., gt=0, description="Importe mensual en guaraníes")


class SalarioBaseUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nuevo_salario: int = Field(
        ..., gt=0, description="Nuevo ingreso mensual de referencia"
    )


class TechoPresupuestarioItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    categoria: str = Field(..., description="Categoría presupuestada")
    limite_mensual: int = Field(
        ..., ge=0, description="Límite máximo fijado para el mes"
    )
    consumido: int = Field(..., ge=0, description="Monto total devengado en el mes")
    porcentaje: float = Field(
        ..., ge=0.0, description="Porcentaje consumido (0.0 a 100.0+)"
    )
    umbral_alerta: int = Field(
        default=80, ge=1, le=100, description="Porcentaje de umbral preventivo"
    )
    alerta_emitida: bool = Field(
        default=False, description="True si supera o iguala el umbral"
    )
    estado: str = Field(default="NORMAL", description="'NORMAL', 'ALERTA' o 'EXCEDIDO'")
    mensaje: str = Field(default="", description="Detalle explicativo")


class ProyectoSimularRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    concepto: str = Field(
        default="Proyecto General", description="Nombre o descripción del proyecto"
    )
    monto: int = Field(..., gt=0, description="Monto total de la inversión / compra")
    meses: int = Field(..., gt=0, description="Cantidad de cuotas o meses a financiar")


class ProyectoSimularResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id_proyecto: str = Field(..., description="ID asignado en estado Simulado")
    concepto: str = Field(..., description="Concepto del proyecto")
    monto_total: int = Field(..., description="Monto total")
    meses: int = Field(..., description="Cantidad de meses")
    cuota_mensual: int = Field(..., description="Monto de la cuota mensual")
    ingreso_base: int = Field(..., description="Ingreso base mensual considerado")
    gastos_fijos: int = Field(..., description="Total gastos fijos")
    cuotas_actuales: int = Field(..., description="Total cuotas de deudas vigentes")
    margen_libre_post_proyecto: int = Field(
        ..., description="Margen libre resultante (MLD)"
    )
    dti_resultante: float = Field(
        ..., description="Ratio de endeudamiento DTI en porcentaje"
    )
    diagnostico: str = Field(..., description="'Viable', 'Ajustado' o 'Riesgo'")
    semaforo: str = Field(..., description="'VERDE', 'AMARILLO' o 'ROJO'")
    mensaje: str = Field(..., description="Detalle del impacto")


class ProyectoAprobarResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="ok")
    id_proyecto: str = Field(..., description="ID del proyecto aprobado")
    estado: str = Field(default="Activo", description="Nuevo estado")
    mensaje: str = Field(
        default="Proyecto aprobado e incorporado como obligación activa."
    )


class EstadoJornadaHoyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fecha: str = Field(..., description="Fecha de hoy (DD/MM/YYYY o YYYY-MM-DD)")
    estado: str = Field(
        default="PENDIENTE",
        description="'PENDIENTE', 'TRABAJANDO', 'COMPLETADO' o 'LIBRE'",
    )
    hora_entrada: Optional[str] = Field(
        default=None, description="Hora de entrada (HH:MM)"
    )
    hora_salida: Optional[str] = Field(
        default=None, description="Hora de salida (HH:MM)"
    )
    minutos_transcurridos: int = Field(
        default=0, ge=0, description="Minutos transcurridos desde la entrada"
    )
    tiempo_transcurrido_formato: str = Field(
        default="0h 00m", description="Tiempo en formato legible"
    )
    puede_marcar_entrada: bool = Field(
        default=True, description="True si puede registrar entrada"
    )
    puede_marcar_salida: bool = Field(
        default=False, description="True si puede registrar salida"
    )
    es_feriado_o_descanso: bool = Field(
        default=False, description="True si es día no laborable"
    )


class BootstrapResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resumen_financiero: dict[str, Any] = Field(
        ..., description="Resumen para tarjetas de dashboard"
    )
    estado_asistencia_hoy: EstadoJornadaHoyResponse = Field(
        ..., description="Estado de la jornada laboral actual"
    )
    clima: dict[str, Any] = Field(
        default_factory=dict, description="Pronóstico y alerta paraguas"
    )
    proximos_avisos: list[dict[str, Any]] = Field(
        default_factory=list, description="Avisos prioritarios"
    )
    proximos_vencimientos: list[dict[str, Any]] = Field(
        default_factory=list, description="Compromisos a vencer"
    )
