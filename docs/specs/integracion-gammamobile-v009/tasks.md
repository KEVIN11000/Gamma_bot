# Lista de Tareas Atómicas (Tasks) — Integración GammaMobile v0.0.9

**Regla de ejecución (Fase 2 SDD):** Se implementará **UNA sola tarea por turno**, verificando que los tests asociados y linters pasen al 100% en la terminal antes de marcar `[x]` y avanzar a la siguiente.

---

- [x] **Tarea 1: Esquemas de Validación Pydantic y DTOs para Nuevos Contratos**
  - **Alcance:**
    - En `src/api/schemas.py`, ampliar `AvisoCreate` con `repeticion: str = "NINGUNA"` e `hitos_minutos: list[int] = Field(default_factory=lambda: [1440])`.
    - Crear clase `AvisoUpdate` con campos opcionales (`titulo`, `fecha_evento`, `repeticion`, `hitos_minutos`, `dias_restantes`).
    - En `src/api/schemas.py`, ampliar `ObligacionCreate` para incluir `entidad`, `saldo_actual`, `cuotas_totales`, `cuotas_restantes`, `dia_vencimiento`, `fecha_inicio`, `estado` (default `"Activo"`).
    - Crear clase `ObligacionUpdate` con campos opcionales para permitir actualizaciones y transiciones de estado (`"Simulado"` $\rightarrow$ `"Activo"`).
  - **Criterio de aceptación:** Tests unitarios de validación en `tests/test_validators.py` y tipado limpio con `mypy src/api/schemas.py`.

- [x] **Tarea 2: Marcación Laboral Real en Google Sheets (`POST /api/v1/asistencia/marcar`)**
  - **Alcance:**
    - En `src/api/blueprint.py`, actualizar `marcar_asistencia()` para resolver `spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""`.
    - Instanciar `AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)` y delegar en `ejecutar_marcado_para_bot(modo=modo)`.
    - Evaluar la respuesta del agente: si comienza con `"❌"` o `"⚠️"`, retornar HTTP 400/409 con `{"tipo": "error", "mensaje": mensaje}`.
    - Si la marcación fue aceptada, retornar HTTP 200 con `tipo` (`"entrada"` o `"salida"`), `hora` (`HH:MM`) y `mensaje` confirmado.
    - Manejar excepciones de red con Google Sheets retornando HTTP 502/500 estructurado.
  - **Criterio de aceptación:** Tests unitarios en `tests/test_mobile_api.py` cubriendo casos de éxito entrada/salida, errores semánticos (400/409) y fallo de conexión, pasando en `pytest`.

- [x] **Tarea 3: Pipeline Financiero, Desglose IVA y Cabeceras Anti-Caché**
  - **Alcance:**
    - En `src/api/blueprint.py`, unificar resolución de `spreadsheet_id` en `get_dashboard_summary()` y `create_movimiento()`.
    - En `create_movimiento()`, aplicar la fórmula paraguaya de IVA (10%, 5%, Exento) para registrar los campos `Monto_Gravado`, `Monto_IVA` y `Clasificacion_IVA` en `Libro_Diario`.
    - En `get_dashboard_summary()`, calcular `margen_libre` llamando a `calcular_margen_de_ataque()` real e inyectar cabeceras HTTP `Cache-Control: no-store, no-cache, must-revalidate`.
  - **Criterio de aceptación:** Tests en `tests/test_mobile_api.py` verificando el cálculo tributario de movimientos y la presencia de cabeceras anti-caché.

- [x] **Tarea 4: CRUD Completo y Sincronización Google Calendar de Avisos (`/api/v1/avisos`)**
  - **Alcance:**
    - En `src/api/blueprint.py`, corregir `get_avisos()` pasando `spreadsheet_id` a `AgenteAutonomoHoras` e invocando `obtener_lista_avisos_calendar()`.
    - En `create_aviso()`, aceptar `repeticion` e `hitos_minutos`, crear el evento en Calendar mediante `agente_horas.guardar_aviso_calendar(...)` y almacenar `event_id` en `src/avisos.json`.
    - Implementar `PUT /api/v1/avisos/<aviso_id>` para actualizar metadatos en `src/avisos.json` y actualizar o recrear el evento en Calendar.
    - En `delete_aviso()`, borrar de `src/avisos.json` y de Calendar con `agente_horas.eliminar_aviso_calendar(event_id)`.
  - **Criterio de aceptación:** Tests en `tests/test_mobile_api.py` cubriendo `GET`, `POST`, `PUT`, `DELETE` con mocks de Calendar y verificación de `avisos.json`.

- [x] **Tarea 5: Deudas — Soporte Simulado/Activo, CRUD en Sheets y Simulación Real (`/api/v1/obligaciones`)**
  - **Alcance:**
    - En `src/repositories/sheets_repository.py`, implementar `delete_obligacion(id_obligacion)` y `update_obligacion(id_obligacion, datos)`.
    - En `src/api/blueprint.py`, actualizar `create_obligacion()` para respetar `req_obj.estado` (`"Simulado"` o `"Activo"`) y persistir campos extendidos (`Entidad`, `Cuotas_Totales`, `Cuotas_Restantes`, etc.).
    - Implementar ruta `PUT /api/v1/obligaciones/<obligacion_id>` para actualizar estado (aprobar simulación) y saldo en `SheetsRepository`.
    - Implementar ruta `DELETE /api/v1/obligaciones/<obligacion_id>` para eliminar el registro de deuda de la hoja `Obligaciones_Maestro`.
    - En `simular_obligacion()`, calcular `margen_actual` invocando a `calcular_margen_de_ataque()` en vez del número fijo 2.000.000.
  - **Criterio de aceptación:** Tests en `tests/test_mobile_api.py` y `tests/test_sheets_repository.py` validando ciclo de vida completo de deuda y simulación dinámica.

- [x] **Tarea 6: Buffer Circular de Logs del Servidor (`GET /api/v1/sistema/logs`)**
  - **Alcance:**
    - En `src/api/blueprint.py`, reemplazar la lista estática en `get_logs()` por la lectura en reversa de las últimas líneas de `src/gen_log.txt`.
    - Parsear cada línea extrayendo `timestamp`, `nivel` y `mensaje`.
    - Soportar parámetro opcional query `?limit=N` (por defecto 20, máximo 100).
    - Incluir fallback estructurado si el archivo de log no existe o está vacío.
  - **Criterio de aceptación:** Tests en `tests/test_mobile_api.py` verificando orden cronológico inverso, parseo correcto y respeto al límite.

- [x] **Tarea 7: Suite Integral de Verificación, Linters y Auditoría Pre-Commit**
  - **Alcance:**
    - Ejecutar suite completa de tests (`pytest`).
    - Validar formato de código con `black --check`.
    - Validar estándares con `flake8`.
    - Validar tipado con `mypy src`.
    - Ejecutar auditoría git (`git status`).
  - **Criterio de aceptación:** 100% de tests pasando, 0 errores en linters y árbol de trabajo limpio.
