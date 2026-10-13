# Bug Assessment: Falla en Cierre Mensual Contable, Silencio de Callbacks y Reseteo de Libros

- **Slug**: monthly-accounting-closing-balance
- **Created**: 2026-10-13T11:58:30-03:00
- **Source**: Telegram Soporte Tickets `TG-05ed602f` y `TG-612d330f` (Bandeja `tickets/inbox/`)
- **Verdict**: valid
- **Severity**: critical

## Report (verbatim or summarized)

> "El Endpoint de cierre mensual ni el botón comando no funciona para los libros contables, el cierre de horas laborales si funciona"
> — Usuario: @Kl4lT0 (2026-10-06T12:31:19Z, Ticket `TG-05ed602f`)

> "El botón o comando de cierre de libros o estadístico no arroja resultado ni error en pantalla, tampoco cambia los ingresos del periodo, debería resetear los y dejar el balance tal cual queda del anterior periodo!"
> — Usuario: @Kl4lT0 (2026-10-06T19:38:51Z, Ticket `TG-612d330f`)

## Symptom

1. Al pulsar el botón "Cierre Mensual Estadístico" (o ejecutar `/cierre_mensual`) y luego seleccionar una opción interactiva ("📅 Cerrar Mes Actual" o "✏️ Elegir mes manualmente"), la interfaz no produce ninguna respuesta ni error en pantalla (silencio absoluto).
2. El endpoint `/cron/cierre-mensual` envía reportes estadísticos en lugar de ejecutar el cierre contable real de libros.
3. El cierre contable no resetea la hoja `Libro_Diario` ni genera el asiento de saldo traspasado; en consecuencia, `obtener_balance()` continúa sumando todos los ingresos y gastos históricos sin separar el nuevo período contable.

## Reproduction

1. En el bot de Telegram, abrir Menú Sistema -> Pulsar "Cierre Mensual Estadístico".
2. El bot despliega el teclado inline con botones `cierre_mensual_actual` y `cierre_mensual_manual`.
3. Pulsar cualquiera de los botones: la rueda de carga desaparece, pero no se emite ningún mensaje, no cambia la pantalla y no hay feedback.
4. Invocar el endpoint `GET /cron/cierre-mensual`: solo se envían PDFs estadísticos (`informe_estadistico_mensual`), sin afectar los libros contables ni ejecutar `execute_monthly_closing()`.

## Suspected Code Paths

- `src/com/handlers/asistencia.py:155` — `@bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_"))`: intercepta vorazmente los callbacks `cierre_mensual_*` antes que `deudas.py` y finaliza silenciosamente (`None`) al no coincidir con sus condiciones internas.
- `src/services/telegram_service.py:34, 37` — Orden de registro de handlers donde `asistencia` precede a `deudas`.
- `src/flask_app.py:278-293` — Endpoint `/cron/cierre-mensual` desacoplado de la lógica contable real (llama a `cron_jobs.informe_estadistico_mensual` en lugar de `financiero.execute_monthly_closing`).
- `src/logic/financiero.py:703-785` — `execute_monthly_closing()` calcula métricas y escribe en `Cierres_Historicos`, pero no limpia ni archiva `Libro_Diario`, ni crea la fila de saldo traspasado para el período nuevo.
- `src/logic/financiero.py:295-336` — `AgenteFinanciero.obtener_balance()` lee todas las filas de `Libro_Diario` acumulando toda la historia sin filtrar por fecha o corte de período.

## Root Cause Hypothesis

**Causa Raíz Directa (Confianza: Alta / 100%)**:
Existen tres fallas concatenadas:
1. **Shadowing de Callbacks:** El handler de `asistencia.py` tiene un selector de prefijo laxo (`startswith("cierre_")`) que devora los callbacks de cierre mensual sin procesarlos.
2. **Desconexión Arquitectónica:** El endpoint de Flask no ejecuta la función de cierre contable, sino un informe puramente estadístico.
3. **Inexistencia de Ciclo de Vida Contable en Google Sheets:** No existe rotación, archivo ni reseteo de la hoja activa `Libro_Diario` tras un cierre, provocando que los balances nunca se recalculen limpios por período.

## Proposed Remediation

**Preferred**:
1. **Corregir el Selector de Callbacks en `asistencia.py`:** Restringir el filtro a callbacks exclusivos de asistencia (ej. `func=lambda call: call.data.startswith("cierre_") and not call.data.startswith("cierre_mensual") and not call.data.startswith("cierre_mes") and not call.data.startswith("cierre_anio")` o usar regex explícita `^cierre_(confirmar|cancelar|iva|descuento)`).
2. **Alinear el Endpoint `/cron/cierre-mensual`:** Invocar `execute_monthly_closing(mes, anio)` y retornar confirmación con el saldo acumulado transferido.
3. **Implementar Reseteo y Traspaso en `execute_monthly_closing()`:**
   - Respaldar y archivar los movimientos del período cerrado (o crear nueva hoja de período similar a Asistencia).
   - Insertar el asiento inicial `"Saldo Inicial / Traspaso Período Anterior"` con el saldo acumulado en `Libro_Diario` para que `obtener_balance()` comience con el saldo neto del mes anterior e ingresos en cero para el nuevo ciclo.
4. **Unificar Comandos y Textos:** Ubicar los handlers de cierre contable en `finanzas.py` o renombrar adecuadamente para evitar confusiones de dominio.

**Files likely to change**:
- `src/com/handlers/asistencia.py`
- `src/com/handlers/deudas.py` (o mover a `src/com/handlers/finanzas.py`)
- `src/flask_app.py`
- `src/logic/financiero.py`
- `tests/test_handlers_deudas.py`
- `tests/test_handlers_asistencia.py`
- `tests/test_financiero.py`

**Tests to add or update**:
- Test unitario validando que `cierre_mensual_actual` no es interceptado por `asistencia.py` y responde adecuadamente.
- Test de integración para `execute_monthly_closing()` que verifique el reseteo de `Libro_Diario` y el asiento inicial del saldo acumulado.
- Test para el endpoint `/cron/cierre-mensual` en `test_admin_logs.py` o similar.

## Risks & Considerations

- **Integridad de Datos Contables:** El reseteo o rotación de `Libro_Diario` debe garantizar que ningún registro previo se pierda (debe asegurarse el respaldo en CSV/hoja histórica antes de cualquier limpieza).
- **Aislamiento de Producción:** Todas las pruebas de Google Sheets deben ser 100% mockeadas con `MagicMock` y fixtures controlados.

## Open Questions

- Decisión de UX: ¿Preferimos rotar la hoja `Libro_Diario` a una nueva pestaña mensual (ej. `Libro_Diario_2026_10`) como hace Asistencia, o limpiar la hoja activa manteniendo el histórico archivado en Drive / `Cierres_Historicos`?
