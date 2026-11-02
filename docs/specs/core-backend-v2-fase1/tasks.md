# CHECKLIST DE TAREAS: CORE BACKEND V2.0.0 (FASE 1)
**Feature:** `core-backend-v2-fase1`  
**Fecha:** 2 de Noviembre de 2026  
**Regla de Ejecución:** Tareas atómicas, secuenciales e independientes. No se inicia una nueva tarea hasta que los tests de la actual pasen en la terminal.

---

## TAREAS DE CONSTRUCCIÓN

- [x] **Tarea 1: Capa de Persistencia Local SQLite y Modelos (`src/repositories/local_repository.py`)**
  - **Descripción:** Crear el repositorio SQLite local (`data/gamma_local.db`) con soporte WAL y timeout de 15s. Implementar las tablas `asistencia_laboral`, `asistencia_materias` y `configuraciones_sistema`. Proveer métodos CRUD atómicos para inserción, consulta y actualización de jornadas y materias.
  - **Criterio de Aceptación:** Test unitario en `tests/test_local_repository.py` verificando inserción en < 15ms, consultas por fecha, modo WAL activo y recuperación ante colisiones.

- [x] **Tarea 2: Refactorización de Dominio y DTO Puro `MarcacionResult`**
  - **Descripción:** Modificar el método de marcación en `AgenteAutonomoHoras` para retornar un DTO puro `MarcacionResult` en lugar de una cadena formateada con emojis. Incorporar la lógica del corte automático a las 17:00 hs (configurable vía `configuraciones_sistema`).
  - **Criterio de Aceptación:** Test en `tests/test_marcacion_dto.py` verificando que la función retorne tipos estructurados sin necesidad de expresiones regulares, y validando la activación del corte automático a las 17:00 hs.

- [x] **Tarea 3: Unificación de Lógica de Deudas y Abonos en `src/logic/financiero.py`**
  - **Descripción:** Consolidar en `financiero.py` los métodos de alta de obligación y amortización de cuotas/abonos para que Telegram y la API REST compartan la misma lógica exacta (`Categoría = "Préstamos / Deudas"`, generación homogénea de asientos en `Libro_Diario` y actualización de cuotas).
  - **Criterio de Aceptación:** Tests unitarios en `tests/test_financiero.py` y `tests/test_handlers_deudas.py` verificando que tanto la llamada desde API como desde bot produzcan asientos y saldos idénticos.

- [x] **Tarea 4: Endpoint REST de Clima para Gamma Mobile (`GET /api/v1/clima`)**
  - **Descripción:** Crear el endpoint `GET /api/v1/clima` protegido por API Key, que reutilice la lógica de consulta a Open-Meteo de `src/logic/cron_jobs.py` y retorne el DTO `ClimaResponse` (temperatura, mín/máx, probabilidad de precipitación y alerta de paraguas).
  - **Criterio de Aceptación:** Test unitario en `tests/test_clima_api.py` verificando respuesta HTTP 200 con el contrato JSON esperado y mocking de la API externa de Open-Meteo.

- [x] **Tarea 5: Modularización del Monolito API (`src/api/v1/*`) y Bump a v2.0.0**
  - **Descripción:** Descomponer `src/api/blueprint.py` en submódulos ordenados dentro de `src/api/v1/` (`routes_health.py`, `routes_dashboard.py`, `routes_asistencia.py`, `routes_movimientos.py`, `routes_obligaciones.py`, `routes_avisos.py`, `routes_cierres.py`, `routes_clima.py`, `routes_soporte.py`). Actualizar versión a `2.0.0` en `VERSION`, `README.md` y endpoints de salud.
  - **Criterio de Aceptación:** Todos los endpoints de `tests/test_mobile_api.py`, `test_balance_dashboard.py` y `test_cierres_api.py` deben responder con éxito sin romper compatibilidad con clientes existentes.

- [x] **Tarea 6: Sincronización y Volcado Bidireccional (DB Local <-> Google Sheets)**
  - **Descripción:** Desarrollar el adaptador de sincronización `src/services/sync_service.py` con métodos `volcar_local_a_sheets()` y `volcar_sheets_a_local()`, y exponer la ruta administrativa `POST /api/v1/asistencia/sync`.
  - **Criterio de Aceptación:** Test unitario en `tests/test_sync_service.py` con mock de Sheets verificando inserción en lote y actualización de bandera `sincronizado_sheets`.

- [x] **Tarea 7: Techos Presupuestarios Variables Configurables y Alertas Tempranas**
  - **Descripción:** Implementar en `src/logic/financiero.py` la verificación de techos presupuestarios por categoría de gasto variable con flag de encendido/apagado en `configuraciones_sistema`. Si el gasto supera el umbral parametrizable (80%), emitir alerta preventiva.
  - **Criterio de Aceptación:** Test unitario en `tests/test_presupuestos_variables.py` validando la alerta al alcanzar el 80% y confirmando que si el feature toggle está apagado no se emiten alertas.

- [x] **Tarea 8: Verificación Integral de Suite de Calidad y Cierre de Fase 1**
  - **Descripción:** Ejecución completa de suites de linters (`black --check`, `flake8`, `mypy`) y suite total de pruebas `pytest` (alcanzando 100% de tests aprobados).
  - **Criterio de Aceptación:** `uv run pytest` pasa al 100%, `mypy` 0 errores, `flake8` 0 errores, `black` 0 desvíos.
