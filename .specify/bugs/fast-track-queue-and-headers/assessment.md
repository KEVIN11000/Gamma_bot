# Bug Assessment: Cola Rápida Síncrona y Tolerancia de Cabeceras en Obligaciones Maestro

- **Slug**: fast-track-queue-and-headers
- **Created**: 2026-10-13T12:40:00-03:00
- **Source**: Telegram Soporte Ticket `TG-4c2e029d` (`repositories/Main-stable/tickets/in_progress/TICKET-TG-4c2e029d.md`)
- **Verdict**: valid
- **Severity**: low

## Report (verbatim or summarized)

> "Hola, necesito que los procesos que no tardan no sean necesariamente encolados de lo contrario tarda más, analizar esa posibilidad igualmente, da la sensación de que tarda más algo que seguro ya tuvo respuesta del servicio externo. Y además necesito que veas la planilla de obligaciones porque donde va cuotas dice tasa interés."
> — Usuario: @Kl4lT0 (2026-09-25T13:50:14Z)

## Symptom

1. **Latencia percibida en procesos rápidos**: Tareas ligeras como agendamiento de avisos en Google Calendar o confirmaciones inmediatas dan la sensación de demora al quedar supeditadas al ciclo de encolado sin despacho síncrono inmediato en el WSGI.
2. **Inconsistencia de cabeceras en Google Sheets**: En la hoja remota `Obligaciones_Maestro`, la columna 10 (J) correspondiente al campo `Cuotas` tiene como encabezado `"Tasa Interés"` (o `"Tasa Interes"`). Al leer con `_get_records(expected_headers=ENCABEZADOS_OBLIGACIONES_MAESTRO)`, se genera un fallo de validación de encabezados que activa el fallback con `expected_headers=[]`, dejando los diccionarios sin la clave `"Cuotas"`, provocando que `d.get("Cuotas")` devuelva `None` o valores por defecto erróneos.

## Reproduction

1. En la hoja de cálculo remota `Obligaciones_Maestro`, la cabecera de la columna J es `"Tasa Interés"`.
2. Al ejecutar cualquier lectura como `SheetsRepository.get_obligaciones_activas()` o `get_todas_obligaciones()`, el diccionario resultante tiene las claves con el nombre literal de la hoja (`"Tasa Interés"`), careciendo de la clave `"Cuotas"`.
3. Todo código que acceda a `d.get("Cuotas")` (por ejemplo, cálculo de cuotas de amortización o proyecciones financieras) no encuentra el dato.

## Suspected Code Paths

- `src/com/handlers/avisos.py:70` — Encolado de aviso calendar (`crear_aviso_calendar`).
- `src/repositories/sheets_repository.py:92-103` — Método `_get_records(ws, expected_headers)`.
- `src/repositories/sheets_repository.py:44-70` — Método `_ensure_headers(ws, sheet_name)`.
- `src/logic/constants.py:84-100` — Definición de `ENCABEZADOS_OBLIGACIONES_MAESTRO`.

## Root Cause Hypothesis

1. **Cola / Despacho Inmediato**: En PythonAnywhere no hay worker persistente. La arquitectura debe aplicar sistemáticamente `sync_fallback=True, bot=bot` a todas las tareas de respuesta al usuario.
2. **Desajuste de Esquema Sheets**: Históricamente la columna J fue nombrada `"Tasa Interés"` en la plantilla remota del usuario, mientras que el código la tipifica y consulta como `"Cuotas"`. Falta un mecanismo de aliasing/normalización tolerante en `_get_records` y una sincronización idempotente en `_ensure_headers`.

## Proposed Remediation

**Preferred**:
1. Asegurar que `enqueue(..., sync_fallback=True, bot=bot)` esté aplicado de forma uniforme en todas las llamadas de interacción directa del bot.
2. En `SheetsRepository._get_records`, normalizar automáticamente los registros devueltos: si la fila no contiene `"Cuotas"`, verificar si existe alguna clave alternativa (`"Tasa Interés"`, `"Tasa Interes"`, `"Tasa de Interés"`, `"Tasa de Interes"`, `"Tasa_Interes"`) y asignar su valor a `r["Cuotas"]` (y viceversa para mantener retrocompatibilidad bidireccional).
3. En `SheetsRepository._ensure_headers`, cuando se inspeccione `Obligaciones_Maestro`, sincronizar y tolerar la columna 10 sin romper ejecuciones.

**Files likely to change**:
- `src/repositories/sheets_repository.py`
- `tests/test_sheets_repository.py`

**Tests to add or update**:
- Test unitario simulando hoja `Obligaciones_Maestro` con cabecera `"Tasa Interés"` en lugar de `"Cuotas"`, validando que `get_obligaciones_activas` y `get_todas_obligaciones` expongan `Cuotas` correctamente normalizado.

## Risks & Considerations

- Bajo riesgo: los cambios son puramente aditivos y tolerantes con esquemas heredados.
