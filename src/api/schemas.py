from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


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
    tipo: str = "Deuda"
    nombre: str
    monto_inicial: int = Field(..., gt=0)
    cuota_referencia_gs: Optional[int] = 0
    observaciones: Optional[str] = ""


class AbonoRequest(BaseModel):
    id_obligacion: str
    monto: int = Field(..., gt=0)
    nro_factura: Optional[str] = "S/N"
    tasa_iva: TasaIVA = TasaIVA.IVA_10


class SimulacionRequest(BaseModel):
    monto: int = Field(..., gt=0)
    meses: int = Field(..., gt=0)
    concepto: Optional[str] = "Simulación General"


class AvisoCreate(BaseModel):
    titulo: str
    fecha_evento: str  # DD/MM/AAAA HH:MM
    dias_restantes: Optional[int] = None


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
