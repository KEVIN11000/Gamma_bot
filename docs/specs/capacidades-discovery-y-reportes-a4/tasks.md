# Checklist de Tareas: Endpoint de Capacidades y Optimización de Reportes A4

## Tareas de Construcción y Verificación

- [x] **Tarea 1: Esquemas Pydantic y DTOs para Capacidades**
  - **Ubicación:** `src/api/schemas.py`
  - **Objetivo:** Definir `RutaEndpointInfo` y `CapacidadesResponse` con tipado estricto y valores por defecto seguros.
  - **Criterio de Aceptación:** `uv run pytest tests/test_api_schemas_v2.py` valida la serialización y deserialización correcta del contrato.

- [x] **Tarea 2: Implementación del Endpoint `GET /api/v1/capacidades`**
  - **Ubicación:** `src/api/v1/routes_capacidades.py` registrado en `v1_bp`
  - **Objetivo:** Implementar la función de introspección dinámica de `current_app.url_map`, agrupando por módulo, extrayendo métodos y docstrings, y retornando `CapacidadesResponse`.
  - **Criterio de Aceptación:** Prueba con `curl` o test unitario en `tests/test_mobile_api.py` devuelve HTTP 200 con el listado completo de rutas activas de la API.

- [x] **Tarea 3: Estandarización de Etiquetas Canónicas en `logic.py` y `excel_service.py`**
  - **Ubicación:** `src/logic/logic.py`, `src/services/excel_service.py`
  - **Objetivo:** Actualizar las etiquetas del cuadro resumen a `Horas del mes`, `Monto por hora`, `Total Monto por Horas`, `IVA 10%`, `TOTAL IVA INCLUIDO`, protegiendo el filtro anti-duplicación contra nombres antiguos y nuevos.
  - **Criterio de Aceptación:** `uv run pytest tests/test_excel_service.py` pasa 100% verde con las nuevas aserciones canónicas.

- [x] **Tarea 4: Calibración Dimensional de ReportLab en `pdf_service.py` (Hoja Única A4)**
  - **Ubicación:** `src/logic/pdf_service.py`
  - **Objetivo:** Configurar márgenes de 1.0 cm, banner unificado de 20 pt, tabla diaria de 7 columnas con padding vertical 2.2 pt y cuadro resumen compacto (2.5 pt padding).
  - **Criterio de Aceptación:** Test unitario en `tests/test_pdf_a4_fit.py` verifica que un mes de 31 días corridos genera estrictamente 1 página (`TOTAL_PAGINAS_GENERADAS == 1`).

- [x] **Tarea 5: Actualización de la Suite de Tests y Documentación Oficial**
  - **Ubicación:** `tests/`, `docs/ESPECIFICACIONES_API_MOBILE.md`, `docs/SYSTEM_MAP.md`
  - **Objetivo:** Registrar el endpoint `GET /api/v1/capacidades` en la tabla de endpoints activos, actualizar el invariante `INV-A4` en el mapa del sistema y verificar suite completa.
  - **Criterio de Aceptación:** `uv run pytest` (516+ tests pasando), `uv run black --check .`, `uv run flake8` y `uv run mypy` sin errores.
