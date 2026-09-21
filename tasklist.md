# Tasklist: [FEAT] v1.15.0 - Comando /soporte en Telegram, Endpoint /admin/logs y Buzón Vigía

**Versión objetivo:** `v1.15.0` (Nueva funcionalidad / Feature release)  
**Rama:** `feat/sistema-vigia`  
**Metodología:** Agency Agents (Pipeline de 4 Fases)  

---

## Fase 1: Planificación (agency-project-manager-senior)
- [x] **1.1. Especificación y Requisitos Aprobados:**
  - [x] Plan de soporte dual para `/soporte` aprobado.
  - [x] Cero spam en Telegram ratificado.
  - [x] Consulta de logs de servidor bajo demanda (patrón buzón).
- [x] **1.2. Desglose de Tareas Atómicas:**
  - [x] Generar este `tasklist.md` con criterios de aceptación verificables.

---

## Fase 2: Arquitectura (agency-software-architect, agency-backend-architect, agency-ux-architect)
- [x] **2.1. Contrato de Comando `/soporte` (SOLID & OCP):**
  - [x] Modo Directo: `/soporte [tipo] <descripción>` con inferencia automática de tipo (bug / sugerencia / soporte).
  - [x] Modo Interactivo: `/soporte` sin argumentos despliega InlineKeyboardMarkup (🐛 Bug, 💡 Sugerencia, ❓ Consulta, ❌ Cancelar).
  - [x] Máquina de estados: `SOPORTE_ESPERANDO_TEXTO` en SQLite `user_states` con TTL y soporte para `/cancelar`.
- [x] **2.2. Contrato de Endpoint `/admin/logs`:**
  - [x] `GET /admin/logs?lines=N` autenticado con header `X-Cron-Secret` o parámetro.
  - [x] Devuelve JSON seguro con array de líneas y timestamp.
- [x] **2.3. Contrato de Vigía Local (`server-logs`):**
  - [x] Comando `python scripts/vigia.py server-logs` que consume `/admin/logs` y muestra las últimas líneas o las guarda en disco local.

---

## Fase 3: Ciclo Dev ↔ QA (agency-backend-architect, agency-evidence-qa)
- [x] **3.1. Tarea B1 - Handler `/soporte` en Telegram (`src/com/handlers/soporte.py`):**
  - [x] Implementar soporte dual (inline directo vs botones interactivos).
  - [x] Integración con máquina de estados persistente (`states.py`).
  - [x] Emisión fail-safe del ticket a GitHub / almacén sin spam en Telegram.
  - [x] Registro en `src/services/telegram_service.py` y comando en `src/com/handlers/base.py`.
- [x] **3.2. Tarea B2 - Endpoint `/admin/logs` en Flask (`src/flask_app.py`):**
  - [x] Implementar endpoint con validación estricta de `CRON_SECRET`.
  - [x] Lectura segura de últimas líneas de `gen_log.txt` e incidentes locales.
- [x] **3.3. Tarea B3 - Integración en Vigía Engine y CLI (`src/vigia_engine.py`, `scripts/vigia.py`):**
  - [x] Añadir método `fetch_server_logs()` en `VigiaEngine`.
  - [x] Añadir subcomando `server-logs` en `scripts/vigia.py`.
  - [x] Enriquecer `sync` para etiquetar tickets provenientes de `/soporte`.
- [x] **3.4. Tarea B4 - Suite de Pruebas Automatizadas:**
  - [x] `tests/test_soporte.py`: Modo directo, modo interactivo, cancelación `/cancelar`.
  - [x] `tests/test_admin_logs.py`: Auth 403, 200 con logs, parámetro lines.
  - [x] `tests/test_handlers_base.py`: Actualización del registro de comandos.
  - [x] Verificación de 100% tests pasando (141 tests) y linters limpios (`black`, `flake8`, `mypy`).
- [x] **3.5. Tarea B5 - Actualización de Versión:**
  - [x] Actualizar `VERSION` a `1.15.0`.

---

## Fase 4: Certificación de Integración (agency-reality-checker)
- [x] **4.1. Auditoría de Seguridad y No Regresión:**
  - [x] Verificación de 0 regresiones en suites existentes (141 tests en verde).
  - [x] Linters y tipado 100% limpios (64 archivos auditados sin advertencias).
- [x] **4.2. Pipeline Completion Report y Gate Humano:**
  - [x] Despliegue v1.15.0 completado y auditado.

---

## Hotfix v1.15.1: Resolución Incidente Vigía GHI-1 / CI-35630665973
- [x] **HF-1. Diagnóstico de Causa Raíz:**
  - [x] Identificado fallo `F824` en `src/com/core/telemetry.py` (`global _COOLDOWN_REGISTRY` innecesario).
  - [x] Identificado bloqueo en `mypy` remoto por exclusión accidental de `mypy.ini` en `.gitignore`.
- [x] **HF-2. Corrección de Código y Configuración:**
  - [x] Remover `global _COOLDOWN_REGISTRY` en `src/com/core/telemetry.py`.
  - [x] Limpiar imports no utilizados en `tests/test_soporte.py`.
  - [x] Des-ignorar `mypy.ini` de `.gitignore` para su seguimiento en git.
  - [x] Bumping de versión a `1.15.1` en `VERSION`.
- [x] **HF-3. Certificación Local Dev ↔ QA:**
  - [x] `black --check .`: 100% aprobado.
  - [x] `flake8 .`: 0 advertencias / 0 errores.
  - [x] `mypy .`: 64 archivos verificados sin errores.
  - [x] `pytest tests/`: 141 tests pasados exitosamente.
- [ ] **HF-4. Gate Humano y Despliegue:**
  - [ ] Solicitar aprobación humana para commit y push a `Main-stable`.
  - [ ] Resolver ticket en Vigía (`python scripts/vigia.py resolve GHI-1`).

