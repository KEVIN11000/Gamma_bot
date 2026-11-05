# Implementation Plan: Paridad Funcional Backend API v2 para Gamma Mobile (Fase 6)

**Feature Branch:** `Main-stable`  
**Created:** 2026-11-04  
**Status:** Planificación (Fase 0 - SDD)  
**Input:** `docs/specs/paridad-backend-mobile-v2-fase6/spec.md` y `docs/ESPECIFICACIONES_API_MOBILE.md` (v2.0.0).

---

## 1. Contexto Técnico y Arquitectura Modular

### 1.1 Stack Tecnológico y Componentes Involucrados
- **Framework Web:** Python / Flask 3.x utilizando Blueprints modulares registrados bajo el prefijo `/api/v1`.
- **Validación y Serialización:** Pydantic v2 para todos los esquemas DTO de entrada y salida en `src/api/schemas.py`.
- **Capa de Persistencia:**
  - `SheetsRepository` (`src/repositories/sheets_repository.py`): interacción con hojas `Presupuesto_Base`, `Obligaciones_Maestro` y `Libro_Diario`.
  - `LocalRepository` (`src/repositories/local_repository.py`): interacción SQLite para jornadas laborales inmediatas (`jornadas`, `asistencias_materias`) y configuraciones locales.
- **Motores de Negocio:**
  - `src/logic/financiero.py`: `obtener_gastos_fijos()`, `actualizar_monto_gasto_fijo()`, `agregar_gasto_fijo()`, `upsert_salario_presupuesto_base()`, `simulate_project()`, `approve_project()`, `evaluar_techo_presupuestario()`.
  - `src/services/asistencia_service.py` / `src/services/excel_service.py` / `src/logic/pdf_service.py`: generación de reportes binarios Excel/PDF.
- **Seguridad:** Decorador `@require_api_key` con blindaje fail-closed y rate limiter activo.

### 1.2 Nuevos Módulos y Rutas a Construir

```
src/api/v1/
├── routes_presupuesto.py     # NUEVO: Blueprint presupuesto_bp (/presupuesto/fijos, /techos, etc.)
├── routes_proyectos.py       # NUEVO: Blueprint proyectos_bp (/proyectos/simular, /proyectos/{id}/aprobar)
├── routes_reportes.py        # NUEVO: Blueprint reportes_bp (/reportes/financiero/excel, /pdf)
├── routes_asistencia.py      # EXTENSIÓN: Agregar GET /asistencia/estado-hoy
└── routes_dashboard.py       # EXTENSIÓN: Agregar GET /bootstrap
```

---

## 2. Contratos de Datos (Pydantic DTOs en `src/api/schemas.py`)

### 2.1 Presupuesto Base y Techos
```python
class GastoFijoItem(BaseModel):
    concepto: str
    monto: int
    concepto_id: str


class PresupuestoFijosResponse(BaseModel):
    salario_base: int
    total_gastos_fijos: int
    categorias: dict[str, list[GastoFijoItem]]


class GastoFijoUpdate(BaseModel):
    nuevo_monto: int = Field(gt=0)


class GastoFijoCreate(BaseModel):
    categoria: str = Field(min_length=1)
    concepto: str = Field(min_length=1)
    monto: int = Field(gt=0)


class SalarioBaseUpdate(BaseModel):
    nuevo_salario: int = Field(gt=0)


class TechoPresupuestarioItem(BaseModel):
    categoria: str
    limite_mensual: int
    consumido: int
    porcentaje: float
    umbral_alerta: int
    alerta_emitida: bool
    estado: str  # "NORMAL" | "ALERTA" | "EXCEDIDO"
    mensaje: str
```

### 2.2 Proyectos de Inversión y Capital
```python
class ProyectoSimularRequest(BaseModel):
    concepto: str = Field(min_length=1)
    monto: int = Field(gt=0)
    meses: int = Field(gt=0)


class ProyectoSimularResponse(BaseModel):
    id_proyecto: str
    concepto: str
    monto_total: int
    meses: int
    cuota_mensual: int
    ingreso_base: int
    gastos_fijos: int
    cuotas_actuales: int
    margen_libre_post_proyecto: int
    dti_resultante: float
    diagnostico: str
    semaforo: str
    mensaje: str


class ProyectoAprobarResponse(BaseModel):
    status: str
    id_proyecto: str
    estado: str
    mensaje: str
```

### 2.3 Asistencia Diaria e Hidratación (Bootstrap)
```python
class EstadoJornadaHoyResponse(BaseModel):
    fecha: str
    estado: str  # "PENDIENTE" | "TRABAJANDO" | "COMPLETADO" | "LIBRE"
    hora_entrada: str | None
    hora_salida: str | None
    minutos_transcurridos: int
    tiempo_transcurrido_formato: str
    puede_marcar_entrada: bool
    puede_marcar_salida: bool
    es_feriado_o_descanso: bool


class BootstrapResponse(BaseModel):
    resumen_financiero: dict[str, Any]
    estado_asistencia_hoy: EstadoJornadaHoyResponse
    clima: dict[str, Any]
    proximos_avisos: list[dict[str, Any]]
    proximos_vencimientos: list[dict[str, Any]]
```

---

## 3. Manejo de Errores, Idempotencia y Caché

1. **Invalidación Inmediata de Caché:**
   Cualquier llamada de mutación en `Presupuesto_Base` (`PUT /fijos/{c}`, `POST /fijos`, `PUT /salario-base`) o en `Obligaciones_Maestro` (`POST /proyectos/{id}/aprobar`) debe invocar `_sheets_cache.clear()` para garantizar que la app móvil y el bot vean los cambios al instante sin esperar expiración de TTL.
2. **Defensa ante Datos Vacíos o Incompletos en Sheets:**
   Si una categoría en `Presupuesto_Base` no tiene límite o el concepto no existe, retornar códigos HTTP apropiados:
   - `404 Not Found` con `{"error": true, "code": "CONCEPTO_NOT_FOUND", "mensaje": "..."}`.
   - `400 Bad Request` si la validación Pydantic falla.
3. **Resiliencia en Bootstrap:**
   Si algún subsistema falla durante el bootstrap (ej. falla la API externa de clima de Open-Meteo), el endpoint debe retornar los bloques financieros y de asistencia operativos y degradar el bloque del clima con un fallback seguro (`"condicion": "No disponible"`), devolviendo `HTTP 200 OK` para no bloquear el inicio de la app.

---

## 4. Estrategia de Pruebas Automatizadas

Se creará una suite de tests dedicada en `tests/`:
1. `tests/test_routes_presupuesto.py`: Pruebas unitarias completas para los 5 endpoints de presupuesto con mocks de `SheetsRepository`.
2. `tests/test_routes_proyectos.py`: Pruebas de simulación y aprobación de proyectos.
3. `tests/test_routes_asistencia_estado_hoy.py`: Pruebas del cálculo de jornada actual y tiempos transcurridos.
4. `tests/test_routes_reportes_financieros.py`: Pruebas de descarga binaria de Excel/PDF.
5. `tests/test_routes_bootstrap.py`: Pruebas de hidratación unificada y resiliencia ante fallos parciales.
