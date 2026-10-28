from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


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
    fecha: Optional[str] = None
    movimiento: TipoMovimiento = TipoMovimiento.GASTO
    proveedor_cliente: str
    nro_factura: Optional[str] = "S/N"
    total: int = Field(..., gt=0)
    categoria: str = "Varios"
    comprobante: TipoComprobante = TipoComprobante.NO_LEGAL
    tasa_iva: TasaIVA = TasaIVA.IVA_10
    id_obligacion: Optional[str] = None
    rastro_foto: Optional[str] = ""
    client_id: Optional[str] = None


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
