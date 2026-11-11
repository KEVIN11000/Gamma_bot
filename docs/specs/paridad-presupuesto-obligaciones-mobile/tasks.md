# Tareas de Implementación (Tasks): Paridad Financiera, Acceso a Presupuesto y Saneamiento de Obligaciones

**Feature:** `paridad-presupuesto-obligaciones-mobile`  
**Fase SDD:** 0 — Especificación y Arquitectura  
**Fecha:** 2026-11-10  

---

## Checklist de Tareas Atómicas

### Bloque A: Presupuesto Base y Gastos Fijos (Backend REST)
- [x] **Tarea 1: Método de Eliminación de Gastos Fijos en `SheetsRepository`**
  - **Archivo:** `src/repositories/sheets_repository.py`
  - **Descripción:** Implementar el método `eliminar_gasto_fijo(concepto: str) -> bool` que localice la fila en `Presupuesto_Base`, la elimine mediante `ws.delete_rows(idx)` e invalide la caché `presupuesto_base`.
  - **Criterio de Aceptación:** Prueba unitaria en `tests/test_sheets_repository.py` validando eliminación efectiva e invalidación de caché.

- [x] **Tarea 2: Endpoint `DELETE /api/v1/presupuesto/fijos/<concepto>`**
  - **Archivo:** `src/api/v1/routes_presupuesto.py`
  - **Descripción:** Crear el endpoint HTTP `DELETE` protegido por `X-API-KEY`. Si el concepto existe, llama al repositorio y retorna 200 con mensaje de éxito; si no existe, retorna 404 Not Found.
  - **Criterio de Aceptación:** Test de integración en `tests/test_routes_presupuesto.py` validando respuestas 200, 404 y 401 (sin API key).

- [x] **Tarea 3: Endpoint `PUT /api/v1/presupuesto/techos/<categoria>` y Persistencia**
  - **Archivos:** `src/api/schemas.py`, `src/api/v1/routes_presupuesto.py`, `src/repositories/local_repository.py`
  - **Descripción:** Añadir el esquema `TechoPresupuestarioUpdate` e implementar la ruta `PUT /presupuesto/techos/<categoria>` que persista el límite y umbral en `LocalRepository` (`PRESUPUESTO_TECHO_<CAT>` y `PRESUPUESTO_UMBRAL_<CAT>`).
  - **Criterio de Aceptación:** Test unitario verificando que tras actualizar el techo, `evaluar_techo_presupuestario` y `GET /presupuesto/techos` reflejan el nuevo límite.

---

### Bloque B: Saneamiento y Deprecación de `Obligaciones_Maestro`
- [x] **Tarea 4: Blindaje Defensivo en `SheetsRepository` y `AgenteFinanciero` para Campos Obsoletos**
  - **Archivos:** `src/logic/financiero.py`, `src/repositories/sheets_repository.py`
  - **Descripción:** Desacoplar lecturas de la columna `Cuotas` priorizando estrictamente `Cuotas_Restantes` y `Cuotas_Totales`. En altas de obligaciones, autocompletar `Cuotas = Cuotas_Totales` y `Event_ID = ""` para preservar integridad de 17 columnas sin exigir estos campos a los clientes.
  - **Criterio de Aceptación:** Pruebas de regresión en `tests/test_financiero.py` y `tests/test_migracion_obligaciones.py` pasando al 100%.

- [x] **Tarea 5: Documentación de Guía de Deprecación de Columnas de Obligaciones**
  - **Archivo:** `docs/history/fase-saneamiento-obligaciones-maestro.md`
  - **Descripción:** Documentar formalmente el estado de las 17 columnas de `Obligaciones_Maestro`, marcando `Cuotas` y `Event_ID` como `[DEPRECATED / LEGACY]` para el mantenimiento del spreadsheet contable.
  - **Criterio de Aceptación:** Documento revisado y enlazado en `docs/SYSTEM_MAP.md`.

---

### Bloque C: Especificación y Contratos para Gamma Mobile (Android)
- [x] **Tarea 6: Actualización de Contratos Móviles en `docs/ESPECIFICACIONES_API_MOBILE.md`**
  - **Archivo:** `docs/ESPECIFICACIONES_API_MOBILE.md`
  - **Descripción:** Añadir los nuevos endpoints (`DELETE /presupuesto/fijos/{concepto}`, `PUT /presupuesto/techos/{categoria}`), junto con la documentación completa de contratos para `PresupuestoScreen` (Salario Base, Gastos Fijos, Techos Variables), Abonos (`POST /obligaciones/abonar`) y Deuda Foco (`GET /obligaciones/foco`).
  - **Criterio de Aceptación:** Contratos JSON y ejemplos de código Retrofit/Kotlin actualizados.

- [x] **Tarea 7: Especificación de UI/UX para `PresupuestoScreen` en `docs/especificacion_gamma_mobile_android.md`**
  - **Archivo:** `docs/especificacion_gamma_mobile_android.md`
  - **Descripción:** Detallar la arquitectura visual de `PresupuestoScreen` en Jetpack Compose:
    - Card de Salario Base editable.
    - Card de Métricas: Total Fijos vs. Margen Libre Proyectado.
    - Lista de Gastos Fijos agrupada por categoría con botones de editar y borrar.
    - Sección de Techos Presupuestarios Variables con barras de progreso y selector de límite.
    - Modal/Diálogo "Nuevo Gasto Fijo".
  - **Criterio de Aceptación:** Mockup descriptivo de composición Jetpack Compose y máquina de estados (`PresupuestoUiState`).
