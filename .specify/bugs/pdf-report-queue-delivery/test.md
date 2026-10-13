# Bug Verification: Entrega de Reporte PDF Bloqueada en Cola Asíncrona

- **Slug**: pdf-report-queue-delivery
- **Tested**: 2026-10-13T12:14:00-03:00
- **Assessment**: ./assessment.md
- **Fix**: ./fix.md
- **Result**: verified

## Summary

La falla de entrega del reporte PDF ha sido verificada y resuelta con éxito. Todas las llamadas al despachador de reportes en `asistencia.py` ahora ejecutan de forma síncrona con fallback (`sync_fallback=True, bot=bot`), eliminando la dependencia de un worker daemon en segundo plano. La suite de pruebas de handlers y worker pasó al 100% y la suite de regresión completa de 142 tests pasó sin errores.

## Checks Performed

| Check | Command / Action | Result | Notes |
|-------|------------------|--------|-------|
| Reproduction (post-fix) | `pytest tests/test_handlers_asistencia.py -k "test_callback_reporte or test_comando_reporte"` | pass | Verifica que al pulsar reporte financiero se envía de inmediato con `sync_fallback=True` |
| New / updated tests | `pytest tests/test_worker.py -k "test_despachar_generar_reporte_financiero or test_sync_fallback_failure_notifies_user"` | pass | Valida generación de documento PDF y notificación de fallback |
| Regression suite | `pytest --ignore=tests/test_api.py --ignore=tests/test_manual.py` | pass | 142 tests superados sin regresiones |
| Lint / type-check | `black --check`, `flake8`, `mypy` | pass | Formato impecable, 0 advertencias de estilo o tipos en archivos modificados |

## Output Excerpts

```text
tests/test_handlers_asistencia.py ....... [100%] (7 passed in 4.38s)
tests/test_worker.py ...... [100%] (6 passed in 3.73s)
============================ 142 passed in 10.85s =============================
black --check: 4 files would be left unchanged.
flake8: Clean (exit 0)
mypy: Success: no issues found in 2 source files
```

## Residual Risks

- En caso de latencia extrema de red hacia la API de Google Sheets (>30 segundos), el timeout de conexión de Telegram podría vencer la petición síncrona; en dicho caso, el manejo seguro captura la excepción y notifica al usuario con reintento en SQLite.

## Recommendation

Cerrar el bug — verificado end-to-end. Marcar el ticket `TG-f378ab36` como resuelto en la bandeja del Vigía.
