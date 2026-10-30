# Implementation Tasks: Remediación de Integridad y Paridad Backend

**Feature Branch**: `feature/remediacion-integridad-backend-v1-18-6`  
**Spec Document**: `docs/specs/remediacion-integridad-backend-v1-18-6/spec.md`  
**Plan Document**: `docs/specs/remediacion-integridad-backend-v1-18-6/plan.md`  
**Status**: Ready for Execution

---

## Checklist de Tareas Atómicas

- [x] **Tarea 1: Corrección Contable de `saldo_inicial` y `flujo_neto` (Módulo 6)**
  - **Archivos**: `src/logic/financiero.py`, `src/api/blueprint.py`, `tests/test_balance_dashboard.py`
  - **Acción**:
    1. En `src/logic/financiero.py:407`, definir `flujo_neto = total_ingresos - total_gastos` y `saldo_acumulado = saldo_inicial + flujo_neto`.
    2. En `src/api/blueprint.py:104-105`, asignar `saldo_acumulado = balance.get("saldo_acumulado", balance.get("saldo_inicial", 0) + flujo_neto)`.
    3. Añadir tests unitarios que verifiquen que un asiento de apertura único no se duplica en el resumen de dashboard ni en el cálculo de balance.
  - **Criterio de Aceptación**: `pytest tests/test_balance_dashboard.py` pasa exitosamente comprobando paridad contable estricta.

- [x] **Tarea 2: Blindaje de `_ensure_headers` en `SheetsRepository` (Módulo 5.1)**
  - **Archivos**: `src/repositories/sheets_repository.py`, `tests/test_sheets_repository.py`
  - **Acción**:
    1. Modificar `_ensure_headers` para verificar si `len(first_row) != len(expected)` en hojas con filas de datos existentes.
    2. Si hay discordancia columnar en una hoja que ya tiene datos, emitir un log de error/advertencia y abstenerse de sobrescribir celda por celda de forma ciega.
    3. Añadir pruebas unitarias que simulen una hoja con datos legacy y verifiquen que no se corrompen sus encabezados.
  - **Criterio de Aceptación**: `pytest tests/test_sheets_repository.py` pasa sin desfasar columnas.

- [x] **Tarea 3: Script de Migración Idempotente para `Obligaciones_Maestro` (Módulo 5.2)**
  - **Archivos**: `scripts/migrar_obligaciones_maestro.py`, `tests/test_migracion_obligaciones.py`
  - **Acción**:
    1. Crear el script `scripts/migrar_obligaciones_maestro.py` con soporte para `--dry-run` y `--apply`.
    2. Implementar la función pura `realinear_fila_obligacion(row: list[str]) -> list[str]` que detecte si falta la columna `Tipo` e inserte `"Deuda"` en el índice 1 (columna 2).
    3. Crear suite de pruebas unitarias para `realinear_fila_obligacion` verificando casos con 15 columnas, 16 columnas y filas vacías.
  - **Criterio de Aceptación**: `pytest tests/test_migracion_obligaciones.py` pasa al 100%.

- [x] **Tarea 4: Reemplazo del Stub en `POST /api/v1/cierres/ejecutar` (Módulo 3.1)**
  - **Archivos**: `src/api/blueprint.py`, `tests/test_cierres_api.py`
  - **Acción**:
    1. En `src/api/blueprint.py:1877` (`ejecutar_cierre`), reemplazar las constantes hardcodeadas (160h, 4.5M Gs) por llamadas a la lógica real de cálculo contable y de asistencia (`AgenteExcel.ejecutar_cierre_periodo_manual` o `execute_monthly_closing` y devengado real de horas).
    2. Devolver respuesta JSON estructurada con los totales liquidados reales y el enlace al PDF generado.
    3. Crear prueba de integración con mocks en `tests/test_cierres_api.py`.
  - **Criterio de Aceptación**: `pytest tests/test_cierres_api.py` pasa validando que no se emiten valores hardcodeados.

- [x] **Tarea 5: Bump de Versión, Linters y Handoff v1.18.6**
  - **Archivos**: `VERSION`, `CHANGELOG.md`, `README.md`, `HANDOFF.md`, `HANDOFF-backend.md`
  - **Acción**:
    1. Incrementar versión a `1.18.6`.
    2. Documentar la remediación de integridad y paridad en `CHANGELOG.md` y `README.md`.
    3. Ejecutar suite completa de calidad: `black`, `flake8`, `mypy` y `pytest`.
    4. Actualizar `HANDOFF.md` marcando la fase completada.
  - **Criterio de Aceptación**: Suite completa de tests y linters en verde.
