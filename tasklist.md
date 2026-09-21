# Tasklist: [STABILITY-TICKET] v1.14.2 - Restauración de retrocompatibilidad, persistencia de estados y robustez de cola

**Prioridad:** Alta / Bloqueante  
**Rama base:** `Main-stable`  
**Metodología:** Agency Agents (Pipeline de 4 Fases: Planificación -> Arquitectura -> Dev/QA -> Certificación)

---

## Fase 1: Planificación (agency-project-manager-senior)
- [x] **1.1. Context Handoff Start-Phase:**
  - [x] Leer y validar `HANDOFF.md` anterior (v1.14.1).
  - [x] Revalidar vigencia de tests base (`pytest tests/ -q` -> 102 passed).
  - [x] Diagnosticar fallos actuales en CI (flake8, black, mypy).
- [x] **1.2. Plan de Implementación y Aprobación:**
  - [x] Crear `implementation_plan.md` detallando arquitectura Modo Dual, validadores, SQLite state persistence, worker dispatcher y sheets mapping.
  - [x] Aprobación explícita del usuario obtenida para ejecución.

---

## Fase 2: Arquitectura (agency-software-architect, agency-backend-architect)
- [x] **2.1. Diseño de Interfaces y Contratos:**
  - [x] Contrato para `src/com/utils/validators.py` (SRP & DRY).
  - [x] Esquema y tabla SQLite `user_states` en `src/com/core/states.py` para persistencia en WSGI.
  - [x] Contrato de despacho y sincronización de cola en `src/app_queue/worker.py` con `timeout=15.0` y fallback síncrono.
  - [x] Mapeo formal de encabezados esperados en `src/repositories/sheets_repository.py` con constantes de dominio.

---

## Fase 3: Ciclo Dev <-> QA (agency-backend-architect, agency-evidence-qa)
- [x] **3.1. Tarea A1 - Validadores Centralizados (DRY):**
  - [x] Crear `src/com/utils/validators.py` con parsing y sanitización de montos, fechas, categorías y cuotas.
  - [x] Pruebas unitarias para `validators.py` (`tests/test_validators.py` - 8 tests pasados).
- [x] **3.2. Tarea A2 - Persistencia de Estados en SQLite (Stateless WSGI):**
  - [x] Refactorizar `src/com/core/states.py` para almacenar estados en SQLite (`cola.db`) con fallback en memoria.
  - [x] Pruebas unitarias de persistencia y TTL/limpieza de estados (`tests/test_states.py` - 4 tests pasados).
- [x] **3.3. Tarea A3 - Modo Dual en Handlers Financieros (OCP):**
  - [x] Restaurar comando directo `/gasto <monto> <desc>` e `/ingreso <monto> <desc>` con IA en `src/com/handlers/finanzas.py`.
  - [x] Mantener flujo interactivo paso a paso cuando se invoca sin argumentos (`/gasto`, `/ingreso`).
  - [x] Desacoplar y limpiar código mal ubicado en `handle_paso3`.
  - [x] Asegurar que `/cancelar` limpie el estado en cualquier punto.
  - [x] Pruebas unitarias para Modo Dual en finanzas (`tests/test_modo_dual.py`).
- [x] **3.4. Tarea A4 - Modo Dual en Handlers de Deudas (OCP):**
  - [x] Restaurar comando directo `/nueva_deuda <entidad> <concepto> <monto> <cuotas> <fecha> [dia]` en `src/com/handlers/deudas.py`.
  - [x] Restaurar comando directo `/abonar <id> <monto> [fecha] [tasa_iva]` en `src/com/handlers/deudas.py`.
  - [x] Mantener flujos interactivos por botones cuando se invocan sin argumentos.
  - [x] Pruebas unitarias para Modo Dual en deudas (`tests/test_modo_dual.py` y `tests/test_handlers_deudas.py`).
- [x] **3.5. Tarea B1 - Robustez de Cola, Despachador y Fallback (Queue Worker):**
  - [x] Conexión SQLite con `timeout=15.0` y transacciones atómicas.
  - [x] Despacho real de operaciones (`registrar_movimiento`, `create_debt`, `register_payment`, `crear_aviso_calendar`, `generar_reporte`).
  - [x] Fallback de ejecución síncrona si SQLite falla o la cola no está disponible.
  - [x] Logging estructurado con `job_id` y resultado.
  - [x] Pruebas unitarias de procesamiento de cola y fallback (`tests/test_worker.py` - 4 tests pasados).
- [x] **3.6. Tarea C1 - Validación Formal de Encabezados en Google Sheets:**
  - [x] Reemplazar `expected_headers=[]` por las constantes formales (`ENCABEZADOS_*`) en `src/repositories/sheets_repository.py`.
  - [x] Actualizar mocks en `tests/test_integration_local.py` y `tests/test_sheets_repository.py`.
  - [x] Pruebas unitarias del repositorio (24 tests pasados).
- [x] **3.7. Tarea C2 - Saneamiento de Linter y CI/CD:**
  - [x] Formatear con `black .` (57 archivos verificados).
  - [x] Resolver advertencias de `flake8` (0 advertencias/errores con configuración CI).
  - [x] Corregir errores de tipado estricto en `mypy .` (0 issues).
  - [x] Validar suite completa con `pytest tests/ -v` (127 tests pasados, 0 fallidos).

---

## Fase 4: Certificación de Integración (agency-reality-checker)
- [x] **4.1. Auditoría Integral y No-Regresión:**
  - [x] Ejecutar localmente `flake8`, `black --check .`, `mypy .`, `bandit` y `pytest`.
  - [x] Validar los 5 Criterios de Aceptación (Definition of Done).
- [ ] **4.2. Pipeline Completion Report:**
  - [x] Generar reporte exhaustivo con evidencias.
  - [ ] Solicitar confirmación humana explícita antes de cualquier commit o despliegue.
