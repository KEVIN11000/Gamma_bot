# Tasks Checklist: Remediación de SyncService y Manejo de Soporte

**Incidente:** `TG-0b665c71`  
**Fecha:** 2026-11-05  
**Estado:** Fase 3 — Verificación y Calidad Completada

---

- [x] **Tarea 1 (Aislamiento de Dominios y Resolución de Hoja en SyncService):**
  - Eliminar de forma absoluta `LIBRO_CONTABLE_ID` de `SyncService.__init__` en `src/services/sync_service.py` y requerir `SPREADSHEET_ID`.
  - Integrar la lectura de `periodo_actual.txt` en `_nombre_hoja_horas` para sincronizar con la pestaña activa del bot.
  - *Criterio de Aceptación:* `SyncService` jamás abre ni hace fallback al libro contable; usa exclusivamente `SPREADSHEET_ID`.

- [x] **Tarea 2 (Búsqueda Secuencial de Filas 2..40, Eliminación de `append_row` y `USER_ENTERED`):**
  - Modificar `volcar_local_a_sheets` en `src/services/sync_service.py` para buscar la primera fila disponible entre 2 y 40 en lugar de `append_row`.
  - Escribir encabezados de fila (A:B), marcas (C:F) y fórmula en Columna G usando `value_input_option="USER_ENTERED"`.
  - Incorporar soporte para parámetro `forzar: bool = False` que permita reubicar y reconciliar registros existentes.
  - *Criterio de Aceptación:* Fechas nuevas se posicionan en la fila contigua inmediata (ej. fila 11) sin saltar a fila 61.

- [x] **Tarea 3 (Manejo de Errores y Logs en `logic.py`):**
  - En `src/logic/logic.py` (`ejecutar_marcado_para_bot` y `ejecutar_corte_automatico`), inspeccionar el diccionario retornado por `volcar_local_a_sheets`. Si `exito` es False, registrar un warning con el detalle sin bloquear la respuesta.
  - *Criterio de Aceptación:* Si Sheets falla, se registra advertencia clara en `gen_log.txt` y SQLite mantiene `sincronizado_sheets = 0`.

- [x] **Tarea 4 (Supresión de Error 400 en Callback de Soporte):**
  - En `src/com/handlers/soporte.py`, interceptar `ApiTelegramException` con mensaje "message is not modified" en `handle_soporte_callback`.
  - *Criterio de Aceptación:* Pulsar repetidamente opciones de soporte no genera trazas de error 400 en `gen_log.txt`.

- [x] **Tarea 5 (Auto-Sync Post-Deploy y Verificación Integral de Suites):**
  - Añadir hook de auto-sincronización en `flask_app.py` (`deploy()`) para conciliar inmediatamente las jornadas tras el despliegue.
  - Actualizar `tests/test_sync_service.py` con pruebas para aislamiento de `SPREADSHEET_ID`, búsqueda secuencial y `USER_ENTERED`.
  - Ejecutar `uv run black`, `uv run flake8`, `uv run mypy` y `uv run pytest` (>= 480 tests pasando).
  - *Criterio de Aceptación:* 484 tests aprobados, linters impecables y árbol de Git limpio.
