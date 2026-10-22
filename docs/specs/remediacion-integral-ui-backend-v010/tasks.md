# Checklist de Tareas Atómicas de Implementación (Tasks)
## Módulo: Remediación Integral UI/UX, Backend Contracts, Estabilización de Marcación y Blindaje de Cuotas Google Sheets (v0.1.0)

- **Fecha:** 20 de Octubre de 2026
- **Versión de Tareas:** 1.0.0
- **Fase SDD:** 0 (Especificación y Arquitectura - Modo Planificador)
- **Estado:** En Revisión (Gate Obligatorio de Planificación)
- **Regla de Ejecución:** Implementar de forma atómica **UNA SOLA TAREA POR TURNO**. No avanzar a la siguiente sin verificar que los tests pasen en la terminal.

---

### Bloque A: Backend Core (`Gamma_bot` / PythonAnywhere) - *Delegado a Sesión de Backend*
> [!NOTE]
> Conforme a la directiva del usuario, el código de `Gamma_bot` no se modifica en este workspace móvil. Los requerimientos de las Tareas 1, 2 y 3 quedaron formalizados en [requerimientos_gamma_bot_v0.1.0.md](file:///e:/PG/vcp-s/GammaMobile/docs/specs/remediacion-integral-ui-backend-v010/requerimientos_gamma_bot_v0.1.0.md) para su desarrollo en sesión de backend.

- [x] **Tarea 1: Documentar `InMemorySheetsCache` para `Gamma_bot`** (Documentado en `requerimientos_gamma_bot_v0.1.0.md`)
- [x] **Tarea 2: Documentar preservación de datos de deudas y abono contable para `Gamma_bot`** (Documentado en `requerimientos_gamma_bot_v0.1.0.md`)
- [x] **Tarea 3: Documentar auto-detección dinámica de período y manejo de HTTP 429 para `Gamma_bot`** (Documentado en `requerimientos_gamma_bot_v0.1.0.md`)

---

### Bloque B: Cliente Móvil (`GammaMobile` / Android) - *Desarrollo Activo*

- [x] **Tarea 4: Eliminar tormenta de peticiones a Sheets en `DashboardViewModel.onScreenVisible()`**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/presentation/dashboard/DashboardViewModel.kt`
    - `app/src/test/java/com/gamma/mobile/presentation/dashboard/DashboardViewModelTest.kt`
  - **Acción:**
    - Modificar `onScreenVisible()` para invocar `loadDashboard(forceRefresh = false, silent = true)`.
    - Permitir que el `DashboardSummaryCalculator` aplique los movimientos `PENDING` sobre el resumen en caché de 15 minutos sin emitir peticiones de red en cada navegación de solapa.
  - **Criterio de Aceptación:** `DashboardViewModelTest` pasa al 100%. Salir y volver al Dashboard no gatilla nuevas llamadas remotas a `getSummary()`.

- [x] **Tarea 5: Homologar modelo `Movimiento` (`proveedorCliente`, `tasaIva`) y sanear mojibake**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/domain/model/Models.kt`
    - `app/src/main/java/com/gamma/mobile/data/local/entity/MovimientoEntity.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/transacciones/NuevaTransaccionScreen.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/sifen/SifenScannerViewModel.kt`
    - `app/src/main/java/com/gamma/mobile/data/worker/SyncMovimientosWorker.kt`
  - **Acción:**
    - Agregar `proveedorCliente: String = "Varios"`, `nroFactura: String = "S/N"`, `tasaIva: String = "10%"` a `Movimiento` y `MovimientoEntity`.
    - Reemplazar en `NuevaTransaccionScreen.kt` todos los strings corruptos: `"FÃ­sica Legal"` $\rightarrow$ `"Física Legal"`, `"â‚²"` $\rightarrow$ `"₲"`, `"ComprÃ©"` $\rightarrow$ `"Compré"`.
    - En `SifenScannerViewModel.kt`, mapear el RUC emisor hacia `proveedorCliente`.
    - En `SyncMovimientosWorker.kt`, no marcar con `Result.retry()` ante errores de validación de cliente HTTP 400.
  - **Criterio de Aceptación:** `./gradlew testDebugUnitTest` pasa al 100%. El JSON emitido contiene `proveedor_cliente` y es aceptado por el backend sin HTTP 400.

- [x] **Tarea 6: Ergonomía Táctil y Anti-Solapamiento en `ObligacionesScreen` y `AvisosScreen`**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/presentation/obligaciones/ObligacionesScreen.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/avisos/AvisosScreen.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/dashboard/DashboardScreen.kt`
  - **Acción:**
    - En `ObligacionesScreen.kt`, cambiar `contentPadding` inferior del `LazyColumn` a `152.dp`.
    - En `AvisosScreen.kt`, cambiar `contentPadding` inferior a `136.dp`.
    - En `DashboardScreen.kt`, retirar el `Spacer(96.dp)` residual emitido fuera del `Box`.
  - **Criterio de Aceptación:** Renderizado visual verificado. Las tarjetas finales de ambas pantallas tienen margen suficiente para accionar los botones de pie sin solaparse con los FABs.

- [x] **Tarea 7: Corregir capa Canvas del scanner SIFEN con estrategia `Offscreen`**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/presentation/sifen/SifenScannerScreen.kt`
  - **Acción:**
    - Aplicar `Modifier.graphicsLayer { compositingStrategy = CompositingStrategy.Offscreen }` al Canvas de `ScannerOverlay`.
  - **Criterio de Aceptación:** La ventana de recorte del scanner dibuja el visor transparente sobre el feed de la cámara en lugar de pintar un marco negro opaco.

- [x] **Tarea 8: Completar DAO de Avisos para persistencia local y sincronización de status bar**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/data/local/dao/AvisoDao.kt`
    - `app/src/main/java/com/gamma/mobile/data/repository/AvisoRepositoryImpl.kt`
    - `app/src/main/java/com/gamma/mobile/ui/theme/Theme.kt`
  - **Acción:**
    - Agregar `insert(entity: AvisoEntity)` y `deleteById(id: String)` en `AvisoDao.kt`.
    - Persistir en Room en `createAviso` y eliminar de Room en `deleteAviso`.
    - En `Theme.kt`, sincronizar `statusBarColor` con el fondo de los `TopAppBar` (`colorScheme.background`).
  - **Criterio de Aceptación:** `./gradlew testDebugUnitTest` pasa al 100%. La base local Room refleja de inmediato altas y bajas de avisos en modo offline.

- [x] **Tarea 9: Conectar llamada `abonarObligacion` en `GammaApi` y `ObligacionesViewModel`**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/data/remote/GammaApi.kt`
    - `app/src/main/java/com/gamma/mobile/data/repository/ObligacionRepositoryImpl.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/obligaciones/ObligacionesViewModel.kt`
    - `app/src/test/java/com/gamma/mobile/presentation/obligaciones/ObligacionesViewModelTest.kt`
  - **Acción:**
    - Declarar `@POST("obligaciones/abonar") suspend fun abonarObligacion(...)` en `GammaApi.kt`.
    - Implementar en `ObligacionRepositoryImpl.kt` e invocarlo desde `ObligacionesViewModel.kt` al registrar el pago de cuotas.
  - **Criterio de Aceptación:** `ObligacionesViewModelTest` pasa exitosamente. El abono actualiza el saldo de la deuda y dispara el egreso contable en el backend.

- [x] **Tarea 10: Verificación final de calidad y suite de Previews en Compose**
  - **Archivos:**
    - `app/src/main/java/com/gamma/mobile/presentation/dashboard/DashboardScreen.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/obligaciones/ObligacionesScreen.kt`
    - `app/src/main/java/com/gamma/mobile/presentation/transacciones/NuevaTransaccionScreen.kt`
  - **Acción:**
    - Añadir componentes anotados con `@Preview` en Jetpack Compose para las vistas intervenidas según la regla de gobernanza visual.
    - Ejecutar suite completa de tests `./gradlew testDebugUnitTest` y verificar compilación limpia.
  - **Criterio de Aceptación:** 100% de tests pasando en terminal, previews de Compose operativas y estado de Git limpio.
