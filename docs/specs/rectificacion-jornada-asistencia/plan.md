# Plan de Arquitectura y Contratos: Rectificación de Jornada Laboral

**Feature:** `rectificacion-jornada-asistencia`  
**Fecha:** 2026-11-05  
**Estado:** Fase 0 — Especificación y Arquitectura  

---

## 1. Contratos de Datos (Pydantic v2)

### Request DTO: `JornadaRectificarRequest`
Ubicación: `src/api/schemas.py`
```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import re

class JornadaRectificarRequest(BaseModel):
    hora_entrada: Optional[str] = Field(None, description="Hora de entrada en formato HH:MM")
    hora_salida_almuerzo: Optional[str] = Field(None, description="Hora de salida a almuerzo HH:MM")
    hora_vuelta_almuerzo: Optional[str] = Field(None, description="Hora de regreso de almuerzo HH:MM")
    hora_salida: Optional[str] = Field(None, description="Hora de salida definitiva HH:MM")
    modo: str = Field(default="normal", description="Modo de jornada: 'normal' o 'directo'")
    sincronizar_sheets: bool = Field(default=True, description="Si True, sincroniza de inmediato a Google Sheets")

    @field_validator("hora_entrada", "hora_salida_almuerzo", "hora_vuelta_almuerzo", "hora_salida")
    @classmethod
    def validar_formato_hora(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", v):
            raise ValueError(f"Formato de hora inválido: '{v}'. Debe ser HH:MM (00:00 - 23:59).")
        return v

    @model_validator(mode="after")
    def validar_consistencia_cronologica(self) -> "JornadaRectificarRequest":
        if self.hora_entrada and self.hora_salida:
            if self.hora_salida < self.hora_entrada:
                raise ValueError("La hora de salida no puede ser anterior a la hora de entrada.")
        if self.hora_salida_almuerzo and self.hora_vuelta_almuerzo:
            if self.hora_vuelta_almuerzo < self.hora_salida_almuerzo:
                raise ValueError("La vuelta de almuerzo no puede ser anterior a la salida de almuerzo.")
        return self
```

### Response DTO: `JornadaRectificarResponse`
Ubicación: `src/api/schemas.py`
```python
class JornadaRectificarResponse(BaseModel):
    status: str = "ok"
    fecha: str
    dia: str
    modo: str
    hora_entrada: Optional[str]
    hora_salida_almuerzo: Optional[str]
    hora_vuelta_almuerzo: Optional[str]
    hora_salida: Optional[str]
    horas_decimal: float
    sincronizado_sheets: bool
    mensaje: str
```

---

## 2. Flujo y Diseño Modular del Endpoint

```
[Cliente HTTP / App / cURL]
           │
           │  PUT /api/v1/asistencia/jornadas/<fecha> (X-API-KEY)
           ▼
[routes_asistencia.py : rectificar_jornada_asistencia]
           │
           ├─ 1. Validar fecha ISO (YYYY-MM-DD)
           ├─ 2. Parsear & Validar body con JornadaRectificarRequest
           │
           ▼
[LocalRepository]
           │
           ├─ 3. repo.obtener_o_crear_jornada(fecha, dia, modo)
           ├─ 4. Calcular horas_decimal = AgenteAutonomoHoras.calcular_horas_jornada(...)
           ├─ 5. repo.actualizar_jornada(fecha, hora_entrada=..., hora_salida=..., horas_decimal=..., sincronizado_sheets=0)
           │
           ▼
[SyncService (Si sincronizar_sheets == True)]
           │
           ├─ 6. SyncService(spreadsheet_id=SPREADSHEET_ID)
           ├─ 7. sync_svc.volcar_local_a_sheets(mes=dt.month, anio=dt.year, modulo="laboral", forzar=True)
           │
           ▼
[Response JSON 200 OK]
```

---

## 3. Matriz de Códigos de Respuesta HTTP
- **`200 OK`**: Jornada actualizada exitosamente en SQLite y reconciliada en Google Sheets (si aplicó).
- **`400 Bad Request`**: Formato de fecha inválido o inconsistencia cronológica en las horas.
- **`401 Unauthorized`**: Ausencia o invalidez de la cabecera `X-API-KEY`.
- **`500 Internal Server Error`**: Excepción no controlada en base de datos.
