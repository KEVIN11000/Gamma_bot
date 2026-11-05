# Tasks Checklist: Paridad Funcional Backend API v2 para Gamma Mobile (Fase 6)

---

- [x] **Tarea 1 (Modelos Pydantic DTOs en `src/api/schemas.py`):** Definir e incorporar todos los esquemas de validación y respuesta para Presupuesto Base, Techos Presupuestarios, Proyectos de Inversión, Estado de Jornada Laboral Diaria y Agregador Bootstrap.
  - *Criterio de Aceptación:* Modelos instanciables con validación estricta de tipos enteros en montos, campos no vacíos y tests de esquemas en `tests/test_api_schemas_v2.py`.

- [x] **Tarea 2 (Blueprint de Presupuesto Base y Techos en `src/api/v1/routes_presupuesto.py`):** Implementar las rutas `GET /presupuesto/fijos`, `PUT /presupuesto/fijos/<concepto>`, `POST /presupuesto/fijos`, `PUT /presupuesto/salario-base` y `GET /presupuesto/techos`. Conectar con `SheetsRepository` e invalidar caché reactivamente tras mutaciones.
  - *Criterio de Aceptación:* `tests/test_routes_presupuesto.py` con >= 6 pruebas unitarias verificando respuestas 200, actualización en hoja, cálculo de techos y manejo de 400/404.

- [x] **Tarea 3 (Blueprint de Proyectos de Inversión en `src/api/v1/routes_proyectos.py`):** Implementar `POST /proyectos/simular` (con cálculo de MLD, DTI, semáforo y guardado como "Simulado") y `POST /proyectos/<id_proyecto>/aprobar` (transición a "Activo" en `Obligaciones_Maestro`).
  - *Criterio de Aceptación:* `tests/test_routes_proyectos.py` verificando simulación completa con ID de proyecto y cambio de estado a Activo tras la aprobación.

- [x] **Tarea 4 (Endpoint de Estado de Jornada Diaria en `src/api/v1/routes_asistencia.py`):** Implementar `GET /asistencia/estado-hoy` consultando `LocalRepository` y la planilla de asistencia activa para devolver estado actual (`PENDIENTE`, `TRABAJANDO`, `COMPLETADO`), hora de entrada, minutos transcurridos y banderas de marcación.
  - *Criterio de Aceptación:* `tests/test_routes_asistencia_estado_hoy.py` validando respuestas correctas para jornada no iniciada, jornada en curso y jornada finalizada.

- [x] **Tarea 5 (Blueprint de Descarga de Reportes Financieros en `src/api/v1/routes_reportes.py`):** Implementar `GET /reportes/financiero/excel` y `GET /reportes/financiero/pdf` permitiendo descargar balances contables del Libro Diario con autenticación `X-API-KEY`.
  - *Criterio de Aceptación:* `tests/test_routes_reportes_financieros.py` verificando `Content-Type` binario y encabezado `Content-Disposition: attachment`.

- [x] **Tarea 6 (Endpoint Agregador de Hidratación en `src/api/v1/routes_dashboard.py`):** Implementar `GET /bootstrap` agrupando en un único round-trip resumen financiero, estado laboral de hoy, clima y vencimientos, con tolerancia a fallos parciales.
  - *Criterio de Aceptación:* `tests/test_routes_bootstrap.py` validando respuesta 200 consolidada incluso si un servicio externo (ej. clima) está degradado.

- [x] **Tarea 7 (Verificación Integral de Calidad y Cierre de Fase):** Ejecución completa de la suite de pruebas automatizadas (`pytest`), validación de linters (`flake8`, `black`) y auditoría estricta de git.
  - *Criterio de Aceptación:* 100% tests aprobados (>= 430 tests), 0 errores de linters y reporte de estado listo para revisión.
