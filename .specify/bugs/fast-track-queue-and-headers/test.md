# Bug Test Verification: Cola Rápida Síncrona y Tolerancia de Cabeceras en Obligaciones Maestro

- **Slug**: fast-track-queue-and-headers
- **Verified At**: 2026-10-13T12:41:00-03:00

## Verification Summary

- **Suite Ejecutada**: `pytest tests/test_sheets_repository.py`
- **Resultados**: 12/12 tests superados (100% passed).
- **Caso Específico Verificado**:
  `test_get_records_header_normalization_cuotas`: Simula una hoja remota donde `expected_headers` falla y la hoja retorna la columna `"Tasa Interés"`. Comprueba que `get_obligaciones_activas()` puebla `Cuotas` y `Tasa_Interes` con el valor exacto numérico.
