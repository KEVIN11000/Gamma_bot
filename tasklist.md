# Tasklist: Hotfix GSpreadException (Empty Headers)

Esta lista detalla las tareas para corregir el error `GSpreadException: the header row in the worksheet contains duplicates: ['']` reportado en los logs del servidor al invocar `get_all_records()`. Este error se introdujo con la actualización de la librería `gspread` (v6.0+).

## Fase 1: Arquitectura y Solución
- [x] **1. Analizar el comportamiento de gspread 6.0+:**
  - *Problema:* `get_all_records` ahora lanza error por defecto si existen columnas vacías o duplicadas en la cabecera.
  - *Solución:* Pasar explícitamente el parámetro `expected_headers=[]` a las llamadas de `get_all_records()` para hacer bypass estricto de la validación y recuperar el comportamiento legacy (necesario por la estructura actual de Google Sheets que usa el usuario).

## Fase 2: Implementación
- [x] **2. Modificar el repositorio (sheets_repository.py):**
  - Reemplazar todas las invocaciones `ws.get_all_records()` por `ws.get_all_records(expected_headers=[])` (11 reemplazos).
- [x] **3. Actualizar Mocks en tests (test_integration_local.py):**
  - Actualizar `FakeWorksheet.get_all_records(self)` a `def get_all_records(self, **kwargs)` para poder recibir el nuevo parámetro en las pruebas.

## Fase 3: Validación y QA
- [x] **4. QA Local:**
  - Ejecutar `pytest tests/ -q` y certificar el estado (102 tests exitosos).

## Fase 4: Despliegue
- [ ] **5. Aprobación y Despliegue:**
  - Presentar *Pipeline Completion Report* al usuario para autorizar explícitamente el despliegue al servidor.
