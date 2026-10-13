# Bug Fix: Falla en Cierre Mensual Contable, Silencio de Callbacks y Reseteo de Libros

- **Slug**: monthly-accounting-closing-balance
- **Fixed**: 2026-10-13T12:28:30-03:00
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Se eliminó el secuestro (*shadowing*) de los callbacks de cierre mensual en `asistencia.py` restringiendo el handler exclusivamente a los callbacks de asistencia. Se implementó en `SheetsRepository` el método `reset_libro_diario_con_saldo_inicial` para limpiar la hoja del período cerrado y asentar la fila con el saldo neto traspasado. Se adaptó `obtener_balance()` y `comando_balance` para discriminar el saldo inicial acumulado, garantizando que los ingresos inicien en cero para el nuevo período y que el balance inicial refleje fielmente el cierre anterior. Por último, se conectó el endpoint `/cron/cierre-mensual` para invocar el cierre contable real con `execute_monthly_closing()`.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `src/com/handlers/asistencia.py` | modified | Se acotó `func=lambda call: call.data in (...)` a los 6 callbacks propios de asistencia, liberando los callbacks de `cierre_mensual*`. |
| `src/repositories/sheets_repository.py` | modified | Se agregó `reset_libro_diario_con_saldo_inicial(saldo_inicial, fecha_str)`. |
| `src/logic/financiero.py` | modified | `execute_monthly_closing` ahora limpia y resetea `Libro_Diario` con el saldo acumulado; `obtener_balance()` discrimina `saldo_inicial`. |
| `src/com/handlers/finanzas.py` | modified | `comando_balance` ahora muestra `🏛️ Saldo Inicial Traspasado` cuando existe y presenta los ingresos del período limpios. |
| `src/flask_app.py` | modified | `/cron/cierre-mensual` ahora ejecuta `execute_monthly_closing` y luego envía los reportes informativos. |
| `tests/test_handlers_asistencia.py` | modified | Se añadió `test_cierre_mensual_no_interceptado_por_asistencia`. |
| `tests/test_handlers_deudas.py` | modified | Se añadieron tests para el comando interactivo y los callbacks `cierre_mensual_actual` y `cierre_mensual_manual`. |
| `tests/test_financiero.py` | modified | Se añadieron tests para `obtener_balance` con `saldo_inicial` y para el reseteo de `Libro_Diario` en `execute_monthly_closing`. |
| `tests/test_admin_logs.py` | modified | Se añadió test para el endpoint `/cron/cierre-mensual`. |

## Diff Highlights

```python
# src/com/handlers/asistencia.py
- @bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_"))
+ @bot.callback_query_handler(
+     func=lambda call: call.data in (
+         "cierre_cancelar", "cierre_confirmar", "cierre_iva_si",
+         "cierre_iva_no", "cierre_descuento_no", "cierre_descuento_si",
+     )
+ )

# src/logic/financiero.py (execute_monthly_closing)
+ next_month = (month % 12) + 1
+ next_year = year + 1 if month == 12 else year
+ fecha_traspaso = f"01/{str(next_month).zfill(2)}/{next_year}"
+ repo.reset_libro_diario_con_saldo_inicial(saldo_acumulado_actual, fecha_traspaso)
```

## Tests Added or Updated

- `tests/test_handlers_asistencia.py::test_cierre_mensual_no_interceptado_por_asistencia`
- `tests/test_handlers_deudas.py::test_handle_cierre_mensual_interactivo`
- `tests/test_handlers_deudas.py::test_callback_cierre_mensual_actual`
- `tests/test_handlers_deudas.py::test_callback_cierre_mensual_manual`
- `tests/test_financiero.py::test_obtener_balance_con_saldo_inicial`
- `tests/test_financiero.py::test_execute_monthly_closing_resets_libro_diario`
- `tests/test_admin_logs.py::test_cron_cierre_mensual_endpoint`

## Local Verification

- Tests de deudas/cierre: `pytest tests/test_handlers_deudas.py` → 9 passed en 2.49s.
- Tests financieros: `pytest tests/test_financiero.py` → 17 passed en 2.15s.
- Tests de endpoints administrativos: `pytest tests/test_admin_logs.py` → 5 passed en 2.47s.
- Tests de aislamiento en asistencia: `pytest tests/test_handlers_asistencia.py` → 8 passed en 2.27s.
- Suite completa de regresión: `pytest` → 149 passed en 7.63s.
- Linters:
  - `black --check` → 9 files checked, 0 formatting issues.
  - `flake8` → 0 errors.
  - `mypy` → 5 files checked, 0 issues.

## Deviations from Assessment

Ninguna.

## Follow-ups

- Ejecutar `speckit-bug-test slug=monthly-accounting-closing-balance` para generar el reporte de verificación formal.
- Resolver los tickets `TG-612d330f` y `TG-05ed602f` en el Vigía.
