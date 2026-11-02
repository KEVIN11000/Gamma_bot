from __future__ import annotations

# Constants used across the Gamma_bot project

from dataclasses import dataclass, field
from pathlib import Path as _Path
from typing import Any

_VERSION_FILE = _Path(__file__).resolve().parents[1] / "VERSION"
VERSION = (
    _VERSION_FILE.read_text(encoding="utf-8").strip()
    if _VERSION_FILE.exists()
    else "0.0.0"
)

# Sheet names
HOJA_LIBRO_DIARIO = "Libro_Diario"
HOJA_LIBRO_DIARIO_TEST = "Libro_Diario_Test"

# Column letter mapping for hour marking
COLUMNAS_LETRAS = {3: "C", 4: "D", 5: "E", 6: "F"}

# Column configurations
COLUMNAS_NORMAL = [
    (3, "Entrada"),
    (4, "S. Almuerzo"),
    (5, "V. Almuerzo"),
    (6, "Salida"),
]
COLUMNAS_DIRECTO = [(3, "Entrada"), (6, "Salida")]

# API limits
MAX_AVISOS_CALENDAR = 15
DIAS_LIMITE_AVISOS = 30

# Week days
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIA_LIBRE = "Domingo"

# Months in Spanish (Paraguay UTC-3 standard)
MESES_ES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Setiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

# Sheet headers
ENCABEZADOS_HORAS = [
    "Dia",
    "Fecha",
    "Hora entrada",
    "Salgo almuerzo",
    "Vuelta almuerzo",
    "Hora salida",
    "Horas",
]
ENCABEZADOS_LIBRO_DIARIO = [
    "Fecha",
    "Movimiento",
    "Proveedor/Cliente",
    "Nro Factura",
    "Neto",
    "IVA",
    "Total",
    "Categoría",
    "Comprobante",
    "Rastro/Foto",
    "Mes",
    "ID_Obligacion",
    "Tasa_IVA",
    "Monto_Gravado",
    "Monto_IVA",
    "Clasificacion_IVA",
]

ENCABEZADOS_CIERRES_HISTORICOS = [
    "ID_Cierre",
    "Mes",
    "Anio",
    "Total_Ingresos",
    "Total_Gastos",
    "Total_Deudas_Pagadas",
    "Debito_Fiscal",
    "Credito_Fiscal",
    "Liquidacion_IVA",
    "Estado_IVA",
    "Margen_Libre_Disponible",
    "Saldo_Acumulado",
    "Fecha_Cierre",
    "Archivo_Backup_Drive",
]

ENCABEZADOS_OBLIGACIONES_MAESTRO = [
    "ID_Obligacion",
    "Tipo",
    "Nombre",
    "Entidad",
    "Monto_Inicial",
    "Saldo_Actual",
    "Estado",
    "Cuota_Referencia_Gs",
    "Fecha_Inicio",
    "Observaciones",
    "Cuotas",
    "Event_ID",
    "Dia_Vencimiento",
    "Cuotas_Totales",
    "Cuotas_Restantes",
    "Orden_Prioridad",
]

ENCABEZADOS_PRESUPUESTO_BASE = [
    "Tipo_Flujo",
    "Categoria",
    "Concepto",
    "Monto_Mensual_Gs",
    "Tipo_Ingreso_Gasto",
    "Observaciones",
]

TIPO_INGRESO = "Ingreso"
TIPO_EGRESO = "Egreso"
ENCABEZADOS_MATERIAS = [
    "Día",
    "Fecha",
    "Hora Teórica",
    "Asistencia Teórica",
    "Hora Práctica",
    "Asistencia Práctica",
]

# Default hourly wage
MONTO_POR_HORA_DEFAULT = "14634"

# Button expiration (seconds)
EXPIRACION_BOTONES_SECONDS = 86400

# Timezone
TIMEZONE = "America/Asuncion"


@dataclass(frozen=True)
class MarcacionResult:
    """DTO puro que encapsula el resultado tipado de una marcación laboral."""

    exito: bool
    tipo: str  # "entrada" | "salida" | "salida_almuerzo" | "vuelta_almuerzo" | "info" | "error"
    hora: str  # "HH:MM"
    mensaje: str  # Mensaje descriptivo
    auto_corte: bool = False
    datos_jornada: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.datos_jornada is None:
            object.__setattr__(self, "datos_jornada", {})

    def to_dict(self) -> dict[str, Any]:
        """Serializa el resultado a diccionario estándar."""
        return {
            "exito": self.exito,
            "tipo": self.tipo,
            "hora": self.hora,
            "mensaje": self.mensaje,
            "auto_corte": self.auto_corte,
            "datos_jornada": dict(self.datos_jornada),
        }

    def formatear_telegram(self) -> str:
        """Formatea el resultado con emojis y estilo Markdown para Telegram."""
        if not self.exito:
            if "⚠️" in self.mensaje or "❌" in self.mensaje or "ℹ️" in self.mensaje:
                return self.mensaje
            return f"❌ {self.mensaje}"

        if self.auto_corte:
            return f"ℹ️ Se aplicó corte automático de jornada a las {self.hora} hs."

        if self.tipo in ("entrada", "salida", "salida_almuerzo", "vuelta_almuerzo"):
            nombres = {
                "entrada": "Entrada",
                "salida_almuerzo": "S. Almuerzo",
                "vuelta_almuerzo": "V. Almuerzo",
                "salida": "Salida",
            }
            nombre_punto = nombres.get(self.tipo, self.tipo.capitalize())
            return f"✅ *{nombre_punto}* registrado a las {self.hora}."

        return self.mensaje

    def __str__(self) -> str:
        return self.formatear_telegram()
