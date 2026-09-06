from __future__ import annotations

# Constants used across the Gamma_bot project

VERSION = "1.8.7"

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
]
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
TIMEZONE = "America/Buenos_Aires"
