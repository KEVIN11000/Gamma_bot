# Checklist de Tareas Atómicas de Implementación (Tasks) — Versión v0.2.0
## Módulo: Proyector de Capacidad de Pago, Pausado de Deudas, Historial de Cierres y Timeline de Vencimientos

- **Fecha:** 20 de Octubre de 2026
- **Versión de Tareas:** 2.0.0
- **Fase SDD:** 0 (Especificación y Arquitectura)
- **Estado:** Pendiente de Inicio (Handoff preparado)

---

### Bloque A: Backend Core (`Gamma_bot` / PythonAnywhere) — *Sesión de Backend*
> [!NOTE]
> Las especificaciones completas para este bloque se encuentran formalizadas en [requerimientos_gamma_bot_v0.2.0.md](file:///e:/PG/vcp-s/GammaMobile/docs/specs/proyector-capacidad-pago-v020/requerimientos_gamma_bot_v0.2.0.md).

- [x] **Tarea 1: Implementar `InMemorySheetsCache` en `SheetsRepository`**
- [x] **Tarea 2: Integridad de deudas, abono contable en `Libro_Diario` y soporte de estado `Pausado`**
- [x] **Tarea 3: Auto-detección dinámica de período en `AgenteAutonomoHoras` y captura de `HTTP 429`**
- [x] **Tarea 4: Crear endpoint `GET /api/v1/cierres` para historial consolidado de cierres**
- [x] **Tarea 5: Exponer endpoints `GET /obligaciones/vencimientos` y `GET /obligaciones/foco`**
- [x] **Tarea 6: Implementar motor de cálculo `POST /obligaciones/proyectar-capacidad`**

---

### Bloque B: Cliente Móvil (`GammaMobile` / Android) — *Sesión de Mobile*

- [x] **Tarea 7: Soporte de Estado `Pausado` en `Obligacion` y filtros en UI**
  - **Archivos:** `Models.kt`, `ObligacionEntity.kt`, `ObligacionesScreen.kt`, `ObligacionesViewModel.kt`
  - **Acción:** Agregar propiedad `esPausada`, pestaña de filtro `Pausadas` y botón de alternancia rápida *"Pausar cuota este mes"*.
  - **Criterio de Aceptación:** Las deudas pausadas se excluyen del cálculo local de compromisos mensuales.

- [x] **Tarea 8: Persistencia Local de Cierres con Room v4**
  - **Archivos:** `CierreEntity.kt`, `CierreDao.kt`, `GammaDatabase.kt`
  - **Acción:** Crear tabla `cierres`, operaciones CRUD en Room y bump de versión a Database v4.
  - **Criterio de Aceptación:** Migración limpia en Room y tests de base de datos pasando.

- [x] **Tarea 9: Conexión de Endpoints en `GammaApi` y Repositorio de Cierres**
  - **Archivos:** `GammaApi.kt`, `CierresRepository.kt`, `CierresRepositoryImpl.kt`
  - **Acción:** Declarar llamadas `@GET("cierres")` y `@Streaming @GET("cierres/reportes/{filename}")`.
  - **Criterio de Aceptación:** Pruebas unitarias de repositorio pasando con datos remotos y fallback en Room.

- [x] **Tarea 10: Pantalla `HistorialCierresScreen` con visualización y descarga de PDF**
  - **Archivos:** `HistorialCierresScreen.kt`, `CierresViewModel.kt`
  - **Acción:** Interfaz con pestañas (Contable/Laboral) y lanzamiento de intent nativo para visualizar PDF.
  - **Criterio de Aceptación:** Visualización fluida de tarjetas y apertura correcta de comprobantes.

- [x] **Tarea 11: Pantalla y ViewModel de `CapacidadPagoScreen` (Simulador de Asignación)**
  - **Archivos:** `CapacidadPagoScreen.kt`, `CapacidadPagoViewModel.kt`
  - **Acción:** Panel con semáforo de viabilidad (Superávit / Ajustado / Déficit), sliders de abonos y switches de exclusión.
  - **Criterio de Aceptación:** El semáforo y los meses ahorrados se recalculan dinámicamente en pantalla.

- [x] **Tarea 12: Previews en Compose y Validación de Calidad Final**
  - **Archivos:** Todas las vistas nuevas y modificadas.
  - **Acción:** Añadir `@Preview` con soporte de tema sobrio y ejecutar `./gradlew testDebugUnitTest`.
  - **Criterio de Aceptación:** 100% de tests pasando en terminal y compilación limpia de APK.
