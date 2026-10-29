# Feature Specification: Paridad y Optimización Integral Backend con Gamma Mobile

**Feature Branch**: `feature/paridad-optimizacion-gammamobile-v1-18-5`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Integración completa de requerimientos de HANDOFF-backend.md para estabilidad y paridad con Gamma Mobile v0.0.12"

---

## User Scenarios & Testing

### User Story 1 - Alineación de Contratos y Esquemas (Priority: P1) 🎯 MVP

Como usuario de Gamma Mobile, al registrar un ingreso o consultar la deuda foco desde la app, quiero que el backend reconozca correctamente el tipo de transacción y devuelva los datos en el formato esperado, para que los ingresos no se imputen como gastos y la pantalla de foco visualice los saldos inmediatamente.

**Why this priority**: Crítico para la consistencia contable: actualmente la app móvil envía `"tipo": "Ingreso"`, pero `MovimientoCreate` espera `"movimiento"`, registrándolo erróneamente como gasto por defecto en Google Sheets.

**Independent Test**: Enviar `POST /api/v1/movimientos` con `{"tipo": "Ingreso", ...}` y comprobar que se almacene con categoría de ingreso; consultar `GET /api/v1/obligaciones/foco` y verificar que los campos clave de la deuda foco estén presentes de forma compatible.

**Acceptance Scenarios**:
1. **Given** un payload con `"tipo": "Ingreso"` o `"tipo": "Gasto"`, **When** se envía a `POST /api/v1/movimientos`, **Then** el esquema Pydantic asigna el tipo correcto y el movimiento se persiste en la sección correspondiente.
2. **Given** una petición a `GET /api/v1/obligaciones/foco`, **When** existe una deuda prioritaria, **Then** la respuesta contiene los campos planos de la deuda junto al contenedor estructurado `deuda_foco`.
3. **Given** un análisis de ticket vía IA/OCR, **When** se retorna la predicción, **Then** el JSON incluye tanto `"tipo"` como `"tipo_movimiento"`.

---

### User Story 2 - Idempotencia y Respuestas Informativas en API (Priority: P2)

Como usuario móvil en condiciones de conectividad inestable, si mi app reintenta el envío de una transacción por timeout de red o si marco asistencia habiendo registrado ya mi entrada, quiero que el backend no duplique filas en Google Sheets y me responda con estado informativo `HTTP 200 OK`, para no ver alertas de fallo falsas ni descuadrar balances.

**Why this priority**: Evita duplicidad de asientos por reintentos de background workers en Android y previene que respuestas informativas sean tratadas como errores HTTP 400.

**Independent Test**: Enviar dos veces el mismo `POST /api/v1/movimientos` con un mismo `client_id` (o header `X-Client-Id`) y verificar que la segunda llamada retorne éxito sin agregar una segunda fila; enviar marcación duplicada y comprobar respuesta 200 con payload informativo.

**Acceptance Scenarios**:
1. **Given** un `client_id` ya registrado en las últimas 24 horas, **When** se reenvía `POST /api/v1/movimientos`, **Then** el servidor retorna `200 OK` informando que ya fue procesado sin duplicar la fila.
2. **Given** un usuario que ya registró su entrada hoy, **When** llama a `POST /api/v1/asistencia/marcar`, **Then** el servidor retorna `200 OK` con `{"tipo": "info", "mensaje": "...", "confirmado_en_planilla": true}`.
3. **Given** un nuevo movimiento contable registrado con éxito, **When** finaliza la inserción, **Then** la caché de Google Sheets (`_sheets_cache`) se invalida de inmediato.

---

### User Story 3 - Cierres Reales y Analíticas MTD Precisas (Priority: P3)

Como usuario administrativo, quiero que el endpoint de cierre mensual ejecute los cálculos contables reales sobre Google Sheets y que las analíticas de horas trabajadas solo computen jornadas completas con salida registrada, para tener métricas salariales devengadas fidedignas.

**Why this priority**: Elimina stubs simulados en cierres mensuales y previene sobrestimaciones salariales por jornadas incompletas.

**Independent Test**: Solicitar `GET /api/v1/asistencia/analiticas` en un día con solo entrada y verificar que las horas no asuman jornada terminada; invocar `POST /api/v1/cierres/ejecutar` y comprobar la integración contable real.

**Acceptance Scenarios**:
1. **Given** una jornada con marcación de entrada pero sin salida registrada, **When** se consultan las analíticas laborales, **Then** las horas devengadas del día no se computan como jornada finalizada.
2. **Given** la consulta de cierres laborales, **When** se llama a `GET /api/v1/asistencia/cierres`, **Then** se retorna el listado de períodos históricos archivados en el sistema.

---

## Requirements

### Functional Requirements

- **FR-001**: `MovimientoCreate` DEBE admitir el alias `"tipo"` mapeado hacia el campo `"movimiento"`.
- **FR-002**: `GET /api/v1/obligaciones/foco` DEBE retornar un payload compatible exponiendo los datos de la deuda foco tanto en la raíz como bajo la clave `"deuda_foco"`.
- **FR-003**: `AIService` y los procesadores de IA DEBEN incluir tanto `"tipo"` como `"tipo_movimiento"` en sus diccionarios de resultado.
- **FR-004**: `POST /api/v1/asistencia/marcar` DEBE responder con `HTTP 200 OK` estructurado ante marcaciones informativas de entrada/salida ya registradas.
- **FR-005**: `POST /api/v1/movimientos` DEBE invalidar reactivamente `_sheets_cache` de `SheetsRepository`.
- **FR-006**: `POST /api/v1/movimientos` DEBE soportar deduplicación por `client_id` (vía JSON o header `X-Client-Id`).
- **FR-007**: `AgenteAutonomoHoras.obtener_analiticas_horas()` DEBE calcular horas y salario devengado acumulado solo considerando días con salida registrada.
- **FR-008**: Se DEBE implementar el endpoint `GET /api/v1/asistencia/cierres` para exponer el historial de cierres laborales.
- **FR-009**: `POST /api/v1/cierres/ejecutar` DEBE conectar con el flujo contable real de cierre.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% de los ingresos registrados desde Gamma Mobile con `"tipo": "Ingreso"` son categorizados como tales en Google Sheets.
- **SC-002**: 0 asientos contables duplicados en reintentos de red con mismo `client_id`.
- **SC-003**: 0 alertas de error 400 en la app móvil al verificar entradas laborales ya registradas.
- **SC-004**: 100% de la suite de pruebas automatizadas pasando (`pytest`) con linters limpios.
