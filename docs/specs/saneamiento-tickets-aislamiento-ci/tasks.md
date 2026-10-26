# Checklist de Tareas Atómicas de Implementación (Tasks) — Saneamiento de Tickets, Blindaje de Telemetría Vigía y Aislamiento de CI

- **Fecha:** 26 de Octubre de 2026
- **Módulo:** Soporte, Telemetría y Suite de Pruebas de API Móvil (`Gamma_bot`)
- **Fase SDD:** 0 (Especificación y Arquitectura)
- **Estado:** Pendiente de Aprobación en Planning Gate (Compuerta de Planificación)

---

### Tareas Atómicas de Ejecución

- [x] **Tarea 1: Saneamiento y purga de registros de prueba en `src/data/tickets.json`**
  - **Archivos:** `src/data/tickets.json`
  - **Acción:** Purgar las 72 entradas de prueba (`TCK-007` a `TCK-078`) generadas por pytest, conservando exclusivamente los 6 tickets canónicos resueltos (`TCK-001` a `TCK-006`) con indentación de 2 espacios y JSON válido.
  - **Criterio de Aceptación:** `python -m json.tool src/data/tickets.json` valida sin errores y `len(json.load(f)) == 6`.

- [x] **Tarea 2: Blindaje y aislamiento hermético en `tests/test_mobile_api.py`**
  - **Archivos:** `tests/test_mobile_api.py`
  - **Acción:** Modificar la firma de `test_soporte_tickets_github_sync_dispatch` para recibir los fixtures `monkeypatch` y `tmp_path`, inicializar un `fake_tickets` efímero en `tmp_path` y redirigir `api.blueprint.TICKETS_FILE` antes de ejecutar las llamadas POST y PATCH. Auditar y certificar que ninguna otra función de prueba en `tests/` llame a `/soporte/tickets` sin aislamiento de archivo.
  - **Criterio de Aceptación:** Ejecutar `uv run pytest tests/test_mobile_api.py` y confirmar que `git status src/data/tickets.json` permanece inalterado (working tree clean sobre ese archivo).

- [ ] **Tarea 3: Auditoría y prueba de verificación de Telemetría Vigía**
  - **Archivos:** `src/com/core/telemetry.py`, `tests/test_mobile_api.py` (o suite dedicada si aplica)
  - **Acción:** Inspeccionar la implementación de `reportar_incidente_vigia()` para confirmar el cooldown de 30 minutos (1800s) por firma SHA-256 y la degradación silenciosa (`except Exception: return False`) ante fallas de red con la API de GitHub.
  - **Criterio de Aceptación:** Prueba empírica comprobando que un fallo en GitHub no levanta excepción no controlada hacia la API de soporte.

- [ ] **Tarea 4: Verificación contractual de endpoint `GET /api/v1/health`**
  - **Archivos:** `src/api/blueprint.py`, `tests/test_mobile_api.py`
  - **Acción:** Verificar que `GET /api/v1/health` retorne status 200 con payload exacto: `status="ok"`, `version="1.18.0"`, `mobile_version="0.0.10"`, y `download_url="https://github.com/KEVIN11000/Gamma_Mobile/releases/latest"`.
  - **Criterio de Aceptación:** `test_mobile_api.py::test_health_check` pasa exitosamente y valida el formato exacto.

- [ ] **Tarea 5: Certificación de Calidad Integral y Linters**
  - **Archivos:** Todos los archivos intervenidos (`src/data/tickets.json`, `tests/test_mobile_api.py`, `src/api/blueprint.py`)
  - **Acción:** Ejecutar la suite completa `uv run pytest`, `uv run flake8` y `uv run black --check` sobre los módulos modificados.
  - **Criterio de Aceptación:** 201/201 tests pasando en verde, linters sin advertencias y working tree limpio de Git.
