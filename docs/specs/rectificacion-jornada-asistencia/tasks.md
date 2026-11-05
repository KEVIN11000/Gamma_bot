# Checklist de Tareas: Rectificación de Jornada Laboral

**Feature:** `rectificacion-jornada-asistencia`  
**Fecha:** 2026-11-05  
**Estado:** Fase 3 — Verificación y Calidad Completada

---

- [x] **Tarea 1 (Contratos de Datos Pydantic):**
  - Definir `JornadaRectificarRequest` y `JornadaRectificarResponse` en `src/api/schemas.py`.
  - Implementar validadores para formato estricto `HH:MM` y coherencia cronológica.
  - *Criterio de Aceptación:* Pruebas unitarias sobre el esquema validando inputs válidos, strings vacíos y rechazo de formatos incorrectos o incoherencias horarias.

- [x] **Tarea 2 (Endpoint REST `PUT /api/v1/asistencia/jornadas/<fecha>`):**
  - Implementar la ruta en `src/api/v1/routes_asistencia.py` protegida con `@require_api_key`.
  - Obtener o crear jornada en `LocalRepository` y persistir los nuevos valores de horas calculando `horas_decimal`.
  - Disparar sincronización inmediata write-through a Google Sheets (`SPREADSHEET_ID`) si `sincronizar_sheets=True` con `forzar=True`.
  - *Criterio de Aceptación:* Respuesta 200 con payload enriquecido reflejando los campos actualizados.

- [x] **Tarea 3 (Pruebas Automatizadas y Suites de Calidad):**
  - Crear archivo de pruebas unitarias y de integración `tests/test_rectificar_jornada.py`.
  - Validar casos: 401 sin API key, 400 por fecha inválida, 400 por hora_salida < hora_entrada, 200 con actualización en SQLite y mock de Sheets.
  - Ejecutar linters (`black`, `flake8`, `mypy`) y suite completa de pruebas `pytest` (>= 484 tests pasando).
  - *Criterio de Aceptación:* 496 tests aprobados, linters limpios y 0 regresiones.
