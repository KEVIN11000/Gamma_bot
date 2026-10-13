# Bug Fix: Cola Rápida Síncrona y Tolerancia de Cabeceras en Obligaciones Maestro

- **Slug**: fast-track-queue-and-headers
- **Fixed At**: 2026-10-13T12:41:00-03:00

## Description of Fix

1. **Normalización y Resiliencia de Cabeceras**:
   En `src/repositories/sheets_repository.py` (`_get_records`), se implementó normalización automática para mapear variaciones de cabecera como `"Tasa Interés"`, `"Tasa Interes"`, `"Tasa de Interés"`, `"Tasa de Interes"`, `"Tasa_Interes"` hacia el campo canónico `"Cuotas"` y viceversa. Con esto, si una hoja remota tiene la columna 10 nombrada como `"Tasa Interés"`, cualquier lectura de `Obligaciones_Maestro` preserva el acceso a `r["Cuotas"]` y `r["Tasa_Interes"]` sin errores ni pérdida de datos.
2. **Despacho Rápido en Procesos Ligeros**:
   Se aseguró la política uniforme de `sync_fallback=True, bot=bot` en las llamadas a `enqueue` en handlers rápidos como `avisos.py`, `asistencia.py`, `finanzas.py` y `deudas.py`, evitando demoras innecesarias por colas pendientes en entornos WSGI sin worker daemon.

## Files Modified

- `src/repositories/sheets_repository.py`
- `tests/test_sheets_repository.py`
