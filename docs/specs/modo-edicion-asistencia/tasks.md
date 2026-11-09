# Checklist de Tareas: Modo de Edición de Asistencia

**Feature:** `modo-edicion-asistencia`  
**Fecha:** 2026-11-05  
**Estado:** Fase 3 — Verificación y Calidad Completada

---

- [x] **Tarea 1 (Lógica y Servicios de Edición de Asistencia):**
  - Implementar en `src/services/asistencia_service.py` las funciones de soporte para:
    - `limpiar_salida_jornada(fecha)`: resetea `hora_salida` y `horas_decimal` a 0 en SQLite y vacía la columna F en Google Sheets con `forzar=True`.
    - `rectificar_jornada_asistencia(fecha, entrada, sal_alm, vta_alm, salida, modo)`: actualiza tramos, recalcula `horas_decimal` y reconcilia con Google Sheets.
  - *Criterio de Aceptación:* Funciones probadas con SQLite temporal y mocks de Sheets, verificando que la salida se anule limpiamente.

- [x] **Tarea 2 (Handlers Conversacionales en Telegram con Seguridad de Clave):**
  - En `src/com/handlers/asistencia.py`, registrar comando `/editar` (y `/editar_asistencia`) y botón inline en menú `/horas`.
  - Capturar `X-API-KEY` con step handler y ejecutar inmediatamente `bot.delete_message` sobre el mensaje del usuario para evitar fugas de credenciales en el chat.
  - Validar clave con `src.api.security.is_valid_api_key`. Si es correcta, mostrar teclado inline:
    - `[ 🔄 Limpiar salida de hoy ]`
    - `[ 📅 Rectificar ayer ]`
    - `[ ✏️ Modificar por fecha ]`
    - `[ ❌ Cancelar ]`
  - Implementar los callback query handlers y flujos de captura de horarios.
  - *Criterio de Aceptación:* Flujo conversacional probado en tests simulando mensajes de Telegram, verificación de eliminación de mensaje y actualización de datos.

- [x] **Tarea 3 (Pruebas Unitarias/Integración y Verificación Integral de Suites):**
  - Crear archivo `tests/test_modo_edicion_asistencia.py` con cobertura completa:
    - Autenticación válida e inválida con borrado de mensaje.
    - Acción rápida de limpiar salida de hoy.
    - Rectificación de fecha anterior.
  - Ejecutar linters (`black`, `flake8`, `mypy`) y suite completa de pruebas `pytest` (>= 496 tests pasando).
  - *Criterio de Aceptación:* Suite completa en verde y 0 regresiones.
