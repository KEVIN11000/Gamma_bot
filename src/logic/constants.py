from __future__ import annotations

# Constants used across the Gamma_bot project

from pathlib import Path as _Path
_VERSION_FILE = _Path(__file__).resolve().parents[1] / "VERSION"
VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip() if _VERSION_FILE.exists() else "0.0.0"

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
    "ID_Cierre", "Mes", "Anio", "Total_Ingresos", "Total_Gastos",
    "Total_Deudas_Pagadas", "Debito_Fiscal", "Credito_Fiscal",
    "Liquidacion_IVA", "Estado_IVA", "Margen_Libre_Disponible",
    "Saldo_Acumulado", "Fecha_Cierre", "Archivo_Backup_Drive",
]

ENCABEZADOS_OBLIGACIONES_MAESTRO = [
    "ID_Obligacion", "Tipo", "Nombre", "Monto_Inicial", "Saldo_Actual",
    "Estado", "Cuota_Referencia_Gs", "Fecha_Inicio", "Observaciones",
    "Cuotas", "Event_ID", "Dia_Vencimiento", "Cuotas_Totales",
    "Cuotas_Restantes", "Orden_Prioridad",
]

ENCABEZADOS_PRESUPUESTO_BASE = [
    "Tipo_Flujo", "Categoria", "Concepto", "Monto_Mensual_Gs",
    "Tipo_Ingreso_Gasto", "Observaciones",
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
