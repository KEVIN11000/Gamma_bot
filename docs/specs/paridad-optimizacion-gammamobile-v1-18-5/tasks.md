# Tasks: Paridad y Optimización Integral Backend con Gamma Mobile

**Input**: Design documents from `docs/specs/paridad-optimizacion-gammamobile-v1-18-5/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Módulo 1 — Alineación de Contratos y Esquemas (Pydantic vs Mobile)

- [x] T001 [US1] Añadir alias `"tipo"` y `populate_by_name=True` en `MovimientoCreate` ([src/api/schemas.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/schemas.py)) y soportar `clientId` / `client_id`.
- [x] T002 [US1] Desempaquetar campos planos de `deuda_foco` en la raíz de `GET /api/v1/obligaciones/foco` ([src/api/blueprint.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/blueprint.py)) manteniendo el objeto hijo para retrocompatibilidad.
- [x] T003 [US1] Añadir paridad dual de claves (`"tipo"` y `"tipo_movimiento"`) en los retornos de IA y OCR ([src/logic/ai_service.py](file:///e:/PG/vcp-s/Gamma_bot/src/logic/ai_service.py)).

---

## Phase 2: Módulo 2 — Respuestas Informativas, Caché y Analíticas MTD

- [x] T004 [US2] Retornar `HTTP 200 OK` estructurado con `tipo: "info"` en `POST /api/v1/asistencia/marcar` ([src/api/blueprint.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/blueprint.py)) cuando la marcación ya fue registrada hoy.
- [x] T005 [US2] Llamar a la invalidación reactiva de `_sheets_cache` de `SheetsRepository` tras registrar movimientos en `POST /api/v1/movimientos`.
- [x] T006 [US3] Condicionar el cálculo de horas y salario devengado en `AgenteAutonomoHoras.obtener_analiticas_horas()` ([src/logic/logic.py](file:///e:/PG/vcp-s/Gamma_bot/src/logic/logic.py)) a que el registro tenga salida confirmada.

---

## Phase 3: Módulo 3 y 4 — Cierres Reales, Endpoint de Historial y Deduplicación

- [x] T007 [US2] Implementar filtro de deduplicación e idempotencia por `client_id` (en payload o header `X-Client-Id`) en `POST /api/v1/movimientos`.
- [x] T008 [US3] Implementar el endpoint `GET /api/v1/asistencia/cierres` ([src/api/blueprint.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/blueprint.py)) para consultar períodos laborales archivados.
- [x] T009 [US3] Conectar `POST /api/v1/cierres/ejecutar` al flujo de cierre contable y laboral real.

---

## Phase 4: Pruebas Unitarias, CI y Verificación Integral

- [x] T010 [P] Actualizar y expandir tests en `tests/test_mobile_api.py`, `tests/test_financiero.py` y `tests/test_asistencia_service.py`.
- [x] T011 Ejecutar suite completa de tests (`pytest`), formato (`black`) y linters (`flake8`, `mypy`).
