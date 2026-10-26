# Especificación Funcional (Spec) — Saneamiento de Tickets, Blindaje de Telemetría Vigía y Aislamiento de CI

- **Fecha:** 26 de Octubre de 2026
- **Módulo:** Soporte, Telemetría y Suite de Pruebas de API Móvil (`Gamma_bot`)
- **Fase SDD:** 0 (Especificación y Arquitectura)
- **Estado:** Listo para revisión de planificación (Planning Gate)

---

## 1. Alcance y Objetivos

Garantizar la integridad referencial y el aislamiento del almacén de soporte (`src/data/tickets.json`) frente a ejecuciones automatizadas de pruebas en local y CI, purgar los tickets espurios inyectados por ejecuciones previas de tests unitarios, verificar la resiliencia de la telemetría Vigía ante fallas de red con la API de GitHub, y certificar el contrato de respuesta del endpoint `/health` requerido por `GammaMobile v0.0.10`.

---

## 2. Casos de Uso del Alcance (Scope)

### UC-1: Saneamiento del Almacén Productivo `tickets.json`
- **Actor:** Sistema / Administrador / API REST.
- **Descripción:** El almacén `src/data/tickets.json` debe contener exclusivamente el historial legítimo de incidencias resueltas (`TCK-001` a `TCK-006`).
- **Precondición:** `src/data/tickets.json` posee registros de prueba generados por ejecuciones de `pytest` (`TCK-007` a `TCK-078`).
- **Postcondición:** 
  - Se eliminan todos los registros espurios generados por tests.
  - El archivo retiene exactamente 6 tickets históricos válidos con estado `"Cerrado"`.
  - El formato JSON mantiene indentación estándar de 2 espacios y codificación UTF-8.

### UC-2: Aislamiento Hermético en Tests de API Móvil (`test_mobile_api.py`)
- **Actor:** Suite de Pruebas Automatizadas (`pytest` / CI).
- **Descripción:** Toda prueba que interactúe con los endpoints de soporte (`POST /api/v1/soporte/tickets`, `PATCH /api/v1/soporte/tickets/<id>`, etc.) debe operar sobre archivos temporales efímeros inyectados vía `monkeypatch` y `tmp_path`.
- **Precondición:** `test_soporte_tickets_github_sync_dispatch` operaba contra el archivo productivo `TICKETS_FILE` por falta de fixture.
- **Postcondición:**
  - `test_soporte_tickets_github_sync_dispatch` utiliza `tmp_path` y `monkeypatch` para desviar `TICKETS_FILE` a un JSON efímero.
  - Cualquier corrida subsiguiente de `pytest tests/test_mobile_api.py` o de la suite completa deja el archivo `src/data/tickets.json` intacto (comprobable vía `git status`).

### UC-3: Auditoría y Blindaje de Telemetría Vigía
- **Actor:** Sistema / Agente Vigía / Módulos de Error.
- **Descripción:** La función `reportar_incidente_vigia()` en `src/com/core/telemetry.py` debe operar con protección anti-inundación (cooldown de 30 minutos por firma de error) y degradación elegante si GitHub API no está disponible o rechaza la conexión, retornando `False` sin romper el flujo principal ni lanzar HTTP 500 al cliente.
- **Entrada:** Excepción capturada, contexto del incidente, origen del reporte.
- **Salida:** `bool` indicando si se despachó exitosamente el reporte, sin excepciones no controladas.

### UC-4: Verificación Contractual de `GET /api/v1/health`
- **Actor:** Cliente Móvil `GammaMobile`.
- **Descripción:** El endpoint de monitoreo y verificación de salud debe exponer la versión de backend, compatibilidad móvil mínima requerida y enlace oficial de actualización.
- **Entrada:** `GET /api/v1/health` (con o sin encabezado de API Key).
- **Salida Esperada (HTTP 200):**
  ```json
  {
    "status": "ok",
    "sheets_connected": true,
    "calendar_connected": true,
    "version": "1.18.0",
    "mobile_version": "0.0.10",
    "download_url": "https://github.com/KEVIN11000/Gamma_Mobile/releases/latest"
  }
  ```

---

## 3. Lo que queda Excluido (No-Scope)

- No se modificarán las interfaces gráficas ni el código fuente de Kotlin en `GammaMobile` (este alcance pertenece exclusivamente a `Gamma_bot`).
- No se alterarán los endpoints contables (`/cierres`, `/obligaciones`, `/balances`) ni los esquemas de Google Sheets.
- No se cambiará la estructura de datos DTO base de soporte (`TicketSoporteRequest`, `TicketSoportePatchRequest`).
- No se eliminarán los 6 tickets históricos válidos (`TCK-001` a `TCK-006`).

---

## 4. Criterios de Aceptación Verificables

1. **Integridad de Almacén:** `src/data/tickets.json` contiene exactamente 6 elementos válidos (`TCK-001` a `TCK-006`), parseables por `json.load()` y formateados con indentación de 2 espacios.
2. **Inmutabilidad en Pruebas:** Tras ejecutar `uv run pytest tests/test_mobile_api.py`, la ejecución de `git status src/data/tickets.json` confirma que el archivo no fue modificado.
3. **Respuesta de la API:** Una petición autenticada a `GET /api/v1/soporte/tickets` retorna una lista JSON de exactamente 6 tickets con estados consistentes.
4. **Verificación de Linters:** `uv run flake8 src/api/blueprint.py tests/test_mobile_api.py` y `uv run black --check src/api/blueprint.py tests/test_mobile_api.py` pasan con código de salida 0.
5. **No Regresión:** Los 201 tests de la suite completa (`uv run pytest`) siguen pasando al 100%.
