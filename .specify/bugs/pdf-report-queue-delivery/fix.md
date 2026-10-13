# Bug Fix: Entrega de Reporte PDF Bloqueada en Cola Asíncrona

- **Slug**: pdf-report-queue-delivery
- **Fixed**: 2026-10-13T12:13:30-03:00
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Se habilitó la política de `sync_fallback=True, bot=bot` en todas las invocaciones a `enqueue("generar_reporte", ...)` en `asistencia.py`, permitiendo la generación síncrona y entrega inmediata de reportes en tiempo real dentro del entorno WSGI de PythonAnywhere. Adicionalmente, se corrigió el import erróneo de `dispatcher`, se unificó la lectura de claves de payload (`hoja` / `nombre_hoja`) en el worker y se añadió notificación de error al usuario en caso de excepciones durante el fallback.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `src/com/handlers/asistencia.py` | modified | Se eliminó el import inexistente de `dispatcher`, se agregaron parámetros `sync_fallback=True, bot=bot` a todas las llamadas a `enqueue` de reportes y se estandarizó la clave `nombre_hoja`. |
| `src/app_queue/worker.py` | modified | Se añadió soporte dual para `nombre_hoja` o `hoja` y se añadió manejo seguro con feedback al usuario en `sync_fallback`. |
| `tests/test_handlers_asistencia.py` | modified | Se actualizaron las aserciones de `enqueue` para validar la presencia de `sync_fallback=True` y la instancia del bot. |
| `tests/test_worker.py` | modified | Se añadieron tests unitarios para `despachar_trabajo` con reporte financiero y para la notificación de usuario en caso de error en `sync_fallback`. |

## Diff Highlights

```python
# src/com/handlers/asistencia.py
- enqueue(chat_id, "generar_reporte", {"tipo": "financiero"})
+ enqueue(
+     chat_id,
+     "generar_reporte",
+     {"tipo": "financiero"},
+     sync_fallback=True,
+     bot=bot,
+ )

# src/app_queue/worker.py
- nombre_hoja = payload.get("nombre_hoja")
+ nombre_hoja = payload.get("nombre_hoja") or payload.get("hoja")
```

## Tests Added or Updated

- `tests/test_handlers_asistencia.py::test_comando_reporte` — Valida llamada con `sync_fallback=True` y bot para finanzas.
- `tests/test_handlers_asistencia.py::test_callback_reporte` — Valida llamada con `sync_fallback=True` y bot al pulsar "💰 Libro Diario".
- `tests/test_worker.py::test_despachar_generar_reporte_financiero` — Valida extracción de datos y despacho de documento PDF por Telegram.
- `tests/test_worker.py::test_sync_fallback_failure_notifies_user` — Valida que ante un fallo en tiempo real se notifique al usuario y se guarde copia en SQLite.

## Local Verification

- Tests unitarios de asistencia: `pytest tests/test_handlers_asistencia.py` → 7 passed en 4.38s.
- Tests unitarios del worker: `pytest tests/test_worker.py` → 6 passed en 3.73s.
- Suite completa de regresión: `pytest` → 142 passed en 10.85s.
- Linters:
  - `black --check` → 4 files passed, cleanly formatted.
  - `flake8` → 0 errors.
  - `mypy` → Success: no issues found.

## Deviations from Assessment

Ninguna. La remediación aplicada siguió exactamente el diseño acordado en `assessment.md`.

## Follow-ups

- Ejecutar `speckit-bug-test slug=pdf-report-queue-delivery` para generar el reporte de verificación formal.
- Resolver el ticket `TG-f378ab36` en la bandeja del Vigía (`python scripts/vigia.py resolve TG-f378ab36`).
