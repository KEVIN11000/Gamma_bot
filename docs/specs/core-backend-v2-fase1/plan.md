# PLAN DE ARQUITECTURA Y CONTRATOS TÉCNICOS: CORE BACKEND V2.0.0 (FASE 1)
**Feature:** `core-backend-v2-fase1`  
**Fecha:** 2 de Noviembre de 2026  
**Estado:** Planificación de Diseño (Fase 0 - SDD)  

---

## 1. ARQUITECTURA GENERAL Y FLUJO DE DATOS (LOCAL-FIRST)

Para proteger el **worker único de PythonAnywhere**, se invierte la dependencia de persistencia:

```
[Cliente: Mobile App / Bot / Web]
               │
               ▼  (HTTP / Webhook)
┌────────────────────────────────────────┐
│     FastAPI / Flask Blueprint v1       │
│      Validación Pydantic Schemas       │
└──────────────────┬─────────────────────┘
                   │
                   ▼  (< 10ms)
┌────────────────────────────────────────┐
│   LOCAL SQLITE STORE (Fuente Primaria) │
│   • asistencia_laboral                 │
│   • asistencia_materias                │
│   • configuraciones                    │
└──────────────────┬─────────────────────┘
                   │
                   ▼  (Asíncrono en Cola / Background Worker)
┌────────────────────────────────────────┐
│      GOOGLE SHEETS SYNC ADAPTER        │
│   Reflejo / Backup en Hoja de Cálculo  │
└────────────────────────────────────────┘
```

---

## 2. ESQUEMA DE BASE DE DATOS LOCAL (`data/gamma_local.db`)

Para garantizar transacciones ACID y evitar bloqueos en disco sobre PythonAnywhere, se implementa una base de datos SQLite con conexión en modo WAL y timeout de 15 segundos:

### 2.1. Tabla `asistencia_laboral`
```sql
CREATE TABLE IF NOT EXISTS asistencia_laboral (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,              -- 'YYYY-MM-DD'
    dia TEXT NOT NULL,                -- 'Lunes', 'Martes', etc.
    hora_entrada TEXT,                -- '08:00'
    hora_salida_almuerzo TEXT,        -- '12:00'
    hora_vuelta_almuerzo TEXT,        -- '13:00'
    hora_salida TEXT,                 -- '17:00'
    modo TEXT NOT NULL DEFAULT 'normal', -- 'normal' (4 puntos) o 'directo' (2 puntos)
    horas_decimal REAL DEFAULT 0.0,   -- Horas totales calculadas
    auto_cerrado INTEGER DEFAULT 0,   -- 1 si fue cerrado por el corte automático
    sincronizado_sheets INTEGER DEFAULT 0, -- 1 si ya se volcó a Sheets
    actualizado_at INTEGER NOT NULL,  -- Timestamp Unix
    UNIQUE(fecha)
);
```

### 2.2. Tabla `asistencia_materias`
```sql
CREATE TABLE IF NOT EXISTS asistencia_materias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,              -- 'YYYY-MM-DD'
    dia TEXT NOT NULL,
    materia TEXT NOT NULL,            -- Nombre de la cátedra universitaria
    tipo_turno TEXT NOT NULL,         -- 'Teoria' o 'Practica'
    hora_entrada TEXT NOT NULL,       -- '18:30'
    presente INTEGER DEFAULT 1,       -- 1 = presente
    sincronizado_sheets INTEGER DEFAULT 0,
    actualizado_at INTEGER NOT NULL
);
```

### 2.3. Tabla `configuraciones_sistema`
```sql
CREATE TABLE IF NOT EXISTS configuraciones_sistema (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'string', -- 'string', 'int', 'bool', 'json'
    descripcion TEXT
);
-- Valores iniciales:
-- ('HORA_SALIDA_DEFECTO', '17:00', 'string', 'Hora de corte automático de jornada laboral')
-- ('PRESUPUESTO_ALERTAS_ACTIVO', 'true', 'bool', 'Activar alertas tempranas de gasto variable')
-- ('PRESUPUESTO_UMBRAL_ALERTA', '80', 'int', 'Porcentaje de gasto para disparar alerta preventiva')
```

---

## 3. CONTRATOS DE DATOS Y DTOS DE DOMINIO (PYDANTIC V2)

### 3.1. DTO de Dominio: `MarcacionResult`
Reemplaza la respuesta en string con emojis por un objeto tipado puro:
```python
@dataclass(frozen=True)
class MarcacionResult:
    exito: bool
    tipo: str  # "entrada" | "salida" | "salida_almuerzo" | "vuelta_almuerzo" | "info" | "error"
    hora: str  # "08:15"
    mensaje: str  # Texto amigable para usuario
    auto_corte: bool = False
    datos_jornada: dict[str, Any] = field(default_factory=dict)
```

### 3.2. Esquema Clima para Mobile: `ClimaResponse`
```python
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
```

### 3.3. Esquema de Sincronización Bidireccional: `SyncRequest` / `SyncResponse`
```python
class SyncRequest(BaseModel):
    direccion: str = Field("local_to_sheets", pattern="^(local_to_sheets|sheets_to_local)$")
    modulo: str = Field("laboral", pattern="^(laboral|materias|todo)$")
    mes: int | None = None
    anio: int | None = None

class SyncResponse(BaseModel):
    exito: bool
    registros_sincronizados: int
    detalles: str
```

---

## 4. ESTRUCTURA MODULAR DEL PAQUETE API (`src/api/v1/`)

El monolito actual se reemplaza por blueprints agrupados bajo el prefijo común `/api/v1`:

```text
src/api/
├── __init__.py               # Ensambla y exporta mobile_api unificado
├── schemas.py                # Contratos y modelos Pydantic v2
├── security.py               # Autenticación require_api_key
└── v1/
    ├── __init__.py           # Registra sub-blueprints
    ├── routes_health.py      # /health, /version (Bump a 2.0.0)
    ├── routes_dashboard.py   # /dashboard/summary
    ├── routes_asistencia.py  # /asistencia/marcar, /asistencia/sync, /asistencia/materias
    ├── routes_movimientos.py # /movimientos, /movimientos/ocr
    ├── routes_obligaciones.py# /obligaciones/*, /obligaciones/proyectar-capacidad
    ├── routes_avisos.py      # /avisos/*
    ├── routes_cierres.py     # /cierres/*, /cierres/ejecutar, /cierres/reportes/*
    ├── routes_clima.py       # /clima (Nuevo endpoint móvil)
    └── routes_soporte.py     # /soporte/tickets, /sistema/logs, /webhooks/github
```

---

## 5. LÓGICA DE CORTE AUTOMÁTICO DE SALIDA (17:00 HS)

1. En el endpoint o tarea periódica de heartbeat/mantenimiento (ej. `cron/heartbeat` o `procesar-cola`):
2. Se consulta la hora local oficial de Paraguay (`America/Asuncion`).
3. Si la hora actual es $\ge$ `HORA_SALIDA_DEFECTO` (17:00):
   - Se consulta la tabla `asistencia_laboral` para la fecha de hoy.
   - Si existe `hora_entrada` pero `hora_salida` es `NULL`:
     - Se asienta `hora_salida = '17:00'`.
     - Se marca `auto_cerrado = 1`.
     - Se recalcula `horas_decimal`.
     - Se encola el trabajo de reflejo para Google Sheets.
     - Se emite una notificación al bot: *"ℹ️ Se aplicó corte automático de jornada a las 17:00 hs."*

---

## 6. ESTRATEGIA DE MIGRACIÓN Y PRESERVACIÓN DE COMPATIBILIDAD

- **Cero roturas en clientes existentes:** La URL base `/api/v1/*` mantiene idénticas todas las rutas, métodos y formatos JSON que ya consume Gamma Mobile.
- **Transición suave de persistencia:** Las lecturas y escrituras laborales y académicas operan sobre SQLite local; un adaptador en segundo plano o el worker actualiza la hoja de Google Sheets para mantener la visibilidad en tiempo real para el usuario sin impactar el tiempo de respuesta HTTP.
- **Suite de Pruebas:** Todos los 240 tests existentes deben seguir pasando al 100%, más la adición de pruebas unitarias para los nuevos submódulos y repositorios locales.
