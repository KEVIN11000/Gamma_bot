# Bug Assessment: Entrega de Reporte PDF Bloqueada en Cola Asíncrona

- **Slug**: pdf-report-queue-delivery
- **Created**: 2026-10-13T11:58:00-03:00
- **Source**: Telegram Soporte Ticket `TG-f378ab36` (Kept in local `tickets/in_progress/TICKET-TG-f378ab36.md`)
- **Verdict**: valid
- **Severity**: critical

## Report (verbatim or summarized)

> "El módulo de reporte al parecer no funciona, al pulsar en reporte PDF del libro diario no retorna nada ni pasado minutos."
> — Usuario: @Kl4lT0 (2026-10-11T12:03:15Z)

Evidencia en logs del servidor (`kevin11000.pythonanywhere.com`):
```text
[2026-10-11 08:50:03] Enqueued job 20 for chat_id 1393634075, operacion generar_reporte
[2026-10-11 08:58:35] Enqueued job 21 for chat_id 1393634075, operacion generar_reporte
[2026-10-11 09:03:15] Ticket de soporte registrado: '[BUG] El módulo de reporte al parecer no funciona...'
```

## Symptom

Al pulsar el botón "💰 Libro Diario" dentro del flujo de `/reporte` (o ejecutar `/reporte finanzas`), el bot responde con el mensaje transitorio *"⏳ Generando tu reporte... te lo envío en instantes."*, pero el archivo PDF nunca llega al usuario. Los trabajos quedan en estado permanente `pendiente` en la base de datos `cola.db`.

## Reproduction

1. Enviar el comando `/reporte` o pulsar el botón `Generar Reporte PDF` en el menú de Asistencia.
2. Pulsar sobre el botón `💰 Libro Diario` (`callback_data="reporte_tipo_finanzas"`).
3. Observar que el bot envía *"⏳ Generando tu reporte... te lo envío en instantes."*.
4. Esperar indefinidamente: el documento PDF no se entrega porque en el servidor WSGI (PythonAnywhere) no hay ningún worker en background consumiendo `cola.db`, y el endpoint `/cron/procesar-cola` no está siendo invocado por ningún cron externo.

## Suspected Code Paths

- `src/com/handlers/asistencia.py:365` — `enqueue(chat_id, "generar_reporte", {"tipo": "financiero"})` llamado sin `sync_fallback=True` ni `bot=bot`.
- `src/com/handlers/asistencia.py:325` — Atajo por comando `/reporte finanzas` llamado sin `sync_fallback=True, bot=bot`.
- `src/com/handlers/asistencia.py:133` — `from com.core.dispatcher import enqueue` (módulo inexistente, produce `ImportError`).
- `src/com/handlers/asistencia.py:306, 429, 467` — Inconsistencia en la clave del payload (`hoja` vs `nombre_hoja` que espera `worker.py:130`).
- `src/app_queue/worker.py:275-295` — Captura genérica de excepciones en `procesar_trabajos_pendientes` que no notifica al usuario si falla la generación del PDF.

## Root Cause Hypothesis

**Causa Raíz Directa (Confianza: Alta / 100%)**:
El handler de reportes en `asistencia.py` encola la tarea en `cola.db` asumiendo la existencia de un daemon en background. Sin embargo, en la arquitectura de producción sobre PythonAnywhere (WSGI con `flask_app.py`), no existen procesos en background permanentes. Para mitigar esto, otros módulos (Finanzas y Deudas) migraron a la política de `sync_fallback=True, bot=bot` (fast-track síncrono que genera y envía el PDF en 3-4 segundos dentro del mismo ciclo). El handler de reportes quedó desacoplado y sin dicho fallback, condenando los trabajos a quedar varados en SQLite.

## Proposed Remediation

**Preferred**:
1. Actualizar las invocaciones a `enqueue` en `src/com/handlers/asistencia.py` (líneas 325, 365, y complementarias de reportes de horas) para incluir `sync_fallback=True, bot=bot`, permitiendo que el reporte se procese y entregue de inmediato vía `despachar_trabajo`.
2. Corregir el import roto en `src/com/handlers/asistencia.py:133` para importar desde `app_queue.worker import enqueue`.
3. Unificar las claves de payload entre `asistencia.py` y `worker.py` (`nombre_hoja`).
4. Añadir feedback explícito al usuario en `despachar_trabajo` si ocurre una excepción de red o de Google Sheets, evitando que el usuario espere sin respuesta.

**Files likely to change**:
- `src/com/handlers/asistencia.py`
- `src/app_queue/worker.py`
- `tests/test_handlers_asistencia.py`
- `tests/test_worker.py`

**Tests to add or update**:
- Test unitario que verifique que al pulsar `reporte_tipo_finanzas`, `enqueue` se invoca con `sync_fallback=True` y la instancia del bot.
- Test de integración simulando `despachar_trabajo` con `operacion="generar_reporte"` que valide la llamada a `PDFService.generar_reporte_generico` y `bot.send_document`.

## Risks & Considerations

- **Tiempo de respuesta HTTP:** La generación de ReportLab + lectura de Sheets toma entre 2 y 4 segundos, lo cual está bien dentro del timeout de webhook de Telegram (30s).
- **Aislamiento de producción:** Las pruebas deben utilizar mocks para `bot.send_document` y `AgenteFinanciero.preparar_datos_reporte`.

## Open Questions

- Ninguna. Causa raíz confirmada empíricamente en código y logs de servidor.
