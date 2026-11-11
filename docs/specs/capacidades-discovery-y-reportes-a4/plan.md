# Plan Arquitectónico: Endpoint de Capacidades y Optimización de Reportes A4

## 1. Arquitectura Modular

```
[Cliente: Gamma Mobile / Bot / Web]
                 │
                 ▼
     [GET /api/v1/capacidades]
                 │
                 ├──► [Introspección URL Map de Flask] (current_app.url_map)
                 ├──► [Filtrado de Rutas /api/v1]
                 ├──► [Extracción de Metadatos y Docstrings]
                 └──► [Respuesta JSON CapacidadesResponse]

[Generador de Reportes Laborales]
                 │
                 ├──► [src/logic/pdf_service.py] ──► Calibración A4 (1.0 cm, 2.2 pt padding, 1 página certificada)
                 ├──► [src/services/excel_service.py] ──► Fórmulas y Etiquetas Canónicas (Horas del mes, Monto por hora...)
                 └──► [src/logic/logic.py] ──► Preparación de datos y escritura defensiva en Google Sheets
```

---

## 2. Contratos de Datos y Esquemas Pydantic

### Esquema de Salida para `GET /api/v1/capacidades`

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class RutaEndpointInfo(BaseModel):
    modulo: str = Field(..., description="Módulo funcional (ej. presupuesto, asistencia, obligaciones)")
    ruta: str = Field(..., description="Ruta relativa o absoluta del endpoint (ej. /api/v1/capacidades)")
    metodos: List[str] = Field(..., description="Lista de métodos HTTP soportados (GET, POST, PUT, DELETE)")
    nombre_endpoint: str = Field(..., description="Identificador interno de Flask (ej. mobile_api.obtener_capacidades)")
    descripcion: str = Field(..., description="Resumen o primera línea del docstring de la función")
    autenticacion: bool = Field(True, description="Indica si el endpoint exige API Key o autenticación")
    parametros: Optional[List[str]] = Field(default_factory=list, description="Parámetros dinámicos en la URL")

class CapacidadesResponse(BaseModel):
    version_api: str = Field(..., description="Versión activa del backend")
    total_rutas: int = Field(..., description="Cantidad total de rutas disponibles")
    modulos: List[str] = Field(..., description="Listado de módulos funcionales descubiertos")
    capacidades_clave: Dict[str, bool] = Field(
        default_factory=dict,
        description="Banderas booleanas de soporte de alto nivel para feature-toggles rápidos"
    )
    rutas: List[RutaEndpointInfo] = Field(..., description="Catálogo exhaustivo de endpoints")
```

---

## 3. Especificación Técnica de Calibración Dimensional PDF (`ReportLab`)

### Geometría y Parámetros en `src/logic/pdf_service.py`
* **Márgenes de Documento:**
  - `topMargin`: `1.0 * cm` (28.35 pt)
  - `bottomMargin`: `1.0 * cm` (28.35 pt)
  - `leftMargin`: `1.0 * cm` (28.35 pt)
  - `rightMargin`: `1.0 * cm` (28.35 pt)
  - **Alto útil disponible:** `841.89 - 56.70 = 785.19 pt`.
* **Banner de Título Unificado:**
  - `Table` de 1 fila y 1 columna, ancho 100% útil (`A4[0] - 2.0*cm = 538.5 pt`).
  - Fondo: `#e6e8ec`, borde: `#1a1a2e`, fuente: `10 pt Bold`, padding vertical: `4 pt`. Altura fija: **20 pt**.
* **Fila de Subtítulo y Metadata:**
  - `Table` de 2 columnas (60% / 40%), fuente 8 pt, color `#555555`. Altura: **16 pt**.
* **Tabla de Asistencia (31 días + encabezado):**
  - Filas: 32 filas en total.
  - Padding vertical: `TOPPADDING = 2.2 pt`, `BOTTOMPADDING = 2.2 pt`.
  - Tipografía: Encabezados 8 pt Bold, Datos 7.5 pt.
  - Altura consumida: **524.80 pt**.
* **Cuadro Resumen Inferior:**
  - Hasta 8 filas (base + ajuste + total factura).
  - Padding vertical: `2.5 pt`, ancho: 240 pt alineado a la derecha.
  - Altura consumida: **136.00 pt**.
* **Espaciadores y Footer:**
  - Espaciadores: `3 + 3 + 6 + 8 = 20 pt`.
  - Footer institucional: `9 pt`.
* **Balance de Página:**
  - Altura total consumida: **725.80 pt** (92.4% de la hoja).
  - Margen libre de resguardo: **59.40 pt (2.1 cm)**.
  - Resultado: **1 sola página garantizada**.

---

## 4. Estandarización de Etiquetas Canónicas

| Clave Interna | Etiqueta Canónica Anterior | Nueva Etiqueta Canónica Estandarizada | Destino |
| :--- | :--- | :--- | :--- |
| `horas_mes` | `mes` | **`Horas del mes`** | Sheets, PDF, Excel |
| `tarifa_hora` | `hora` | **`Monto por hora`** | Sheets, PDF, Excel |
| `monto_horas` | `por Horas` | **`Total Monto por Horas`** | Sheets, PDF, Excel |
| `iva_10` | `IVA 10%` | **`IVA 10%`** | Sheets, PDF, Excel |
| `subtotal_iva` | `INCLUIDO` | **`TOTAL IVA INCLUIDO`** | Sheets, PDF, Excel |
| `saldo_ant` | `SALDO ANTERIOR` | **`SALDO ANTERIOR`** / Ajuste | Sheets, PDF, Excel |
| `factura_tot` | `FACTURA` | **`TOTAL FACTURA`** | Sheets, PDF, Excel |

### Filtro Defensivo en `src/logic/logic.py`
Para evitar eliminar o confundir el cuadro resumen en re-ejecuciones de cierre:
```python
# Filtro robusto que tolera tanto etiquetas antiguas como nuevas
f[0].strip().lower() not in ("resumen", "mes", "horas del mes")
```

---

## 5. Manejo de Errores y Seguridad
* **Protección del endpoint `/capacidades`:**
  - Decorador `@require_api_key` activo para evitar scraping público no autorizado.
  - Ocultamiento de endpoints privados o de depuración (`test_*`, `static`).
  - Cache en memoria de la lista de rutas para responder en < 5 ms sin impacto de CPU.
