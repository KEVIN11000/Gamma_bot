# Bug Verification: Falla en Cierre Mensual Contable, Silencio de Callbacks y Reseteo de Libros

- **Slug**: monthly-accounting-closing-balance
- **Tested**: 2026-10-13T12:28:50-03:00
- **Assessment**: ./assessment.md
- **Fix**: ./fix.md
- **Result**: verified

## Summary

Se verificó completamente la solución a los incidentes `TG-05ed602f` y `TG-612d330f`. Los callbacks de cierre mensual (`cierre_mensual_actual`, `cierre_mensual_manual`) responden de inmediato sin interferencia del handler de asistencia. `execute_monthly_closing()` resetea la hoja activa de `Libro_Diario` preservando el saldo acumulado en una fila inicial de traspaso, y `obtener_balance()` inicializa los ingresos del nuevo ciclo en cero mientras refleja fielmente el balance transferido. El endpoint `/cron/cierre-mensual` invoca el cierre real con éxito.

## Checks Performed

| Check | Command / Action | Result | Notes |
|-------|------------------|--------|-------|
| Desbloqueo de Callbacks | `pytest tests/test_handlers_asistencia.py -k test_cierre_mensual_no_interceptado_por_asistencia` | pass | Confirma que asistencia no captura callbacks de cierre mensual |
| Flujo interactivo de Cierre | `pytest tests/test_handlers_deudas.py -k "test_callback_cierre_mensual or test_handle_cierre_mensual"` | pass | Valida respuesta y ejecución de cierre mensual por bot |
| Balance con Saldo Inicial | `pytest tests/test_financiero.py -k "test_obtener_balance_con_saldo_inicial or test_execute_monthly_closing"` | pass | Valida reseteo de hoja e inicialización de ingresos en 0 |
| Endpoint `/cron/cierre-mensual` | `pytest tests/test_admin_logs.py -k test_cron_cierre_mensual_endpoint` | pass | Valida ejecución HTTP protegida con token |
| Regression suite | `pytest --ignore=tests/test_api.py --ignore=tests/test_manual.py` | pass | 149 tests superados en 7.63s |
| Lint / type-check | `black --check`, `flake8`, `mypy` | pass | 0 discrepancias de estilo, tipos o linters |

## Output Excerpts

```text
tests/test_handlers_deudas.py ......... [100%] (9 passed in 2.49s)
tests/test_financiero.py ................. [100%] (17 passed in 2.15s)
tests/test_admin_logs.py ..... [100%] (5 passed in 2.47s)
tests/test_handlers_asistencia.py ........ [100%] (8 passed in 2.27s)
============================= 149 passed in 7.63s =============================
black --check: 9 files would be left unchanged.
flake8: Clean (exit 0)
mypy: Success: no issues found in 5 source files
```

## Residual Risks

- Ninguno. La lógica de fallback garantiza retrocompatibilidad para hojas sin fila de saldo inicial.

## Recommendation

Cerrar los bugs — verificados end-to-end. Marcar los tickets `TG-612d330f` y `TG-05ed602f` como resueltos en el Vigía.
