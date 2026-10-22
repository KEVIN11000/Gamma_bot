# Especificación de Requerimientos (Spec)
## Módulo: Remediación Integral UI/UX, Backend Contracts, Estabilización de Marcación y Blindaje de Cuotas Google Sheets (v0.1.0)

- **Fecha:** 20 de Octubre de 2026
- **Versión de Especificación:** 1.0.0
- **Fase SDD:** 0 (Especificación y Arquitectura - Modo Planificador)
- **Estado:** En Revisión (Gate Obligatorio de Planificación)
- **Repositorios Involucrados:** `GammaMobile` (Cliente Android) y `Gamma_bot` (Backend Core / PythonAnywhere)

---

## 1. Contexto y Objetivos

A partir de la re-auditoría integral de UI/UX, contratos de backend y el diagnóstico empírico del flujo de marcación, se identificaron fallas críticas que bloquean el funcionamiento de la aplicación en producción:
1. **Bloqueo del Registro de Gastos:** `POST /api/v1/movimientos` falla con `HTTP 400` porque el backend exige `proveedor_cliente` como campo obligatorio no opcional, mientras que la app móvil no lo envía. Esto encola reintentos infinitos en `SyncMovimientosWorker`, sin llegar nunca a asentarse en Google Sheets.
2. **Pérdida de Datos en Obligaciones:** Al consultar `GET /api/v1/obligaciones`, el backend cercena las cuotas, entidad y vencimiento; la app móvil sobreescribe Room v3 con valores vacíos.
3. **Agotamiento de Cuotas de Google Sheets API (`HTTP 429`):** El cliente Android fuerza refrescos remotos en cada evento de navegación (`onScreenVisible` con `forceRefresh = true`), y el servidor Flask no implementa caché en memoria, realizando hasta 4 llamadas a Sheets por cada visualización de pantalla y agotando el límite de 60 req/min por service account.
4. **Falsa Desconexión en Marcación:** Las marcaciones laborales fallan con `HTTP 502` / `HTTP 429` debido al colapso de cuotas de Sheets, sumado a la ausencia de `periodo_actual.txt` en el servidor (que forzaba un fallback a `"Mayo 2026"`).
5. **Defectos de UI/UX y Renderizado:** Bloqueo táctil del último elemento en `ObligacionesScreen` tapado por dos FABs (136 dp vs 96 dp de padding), ventana negra en el scanner SIFEN por falta de capa `Offscreen` en Canvas, y textos corruptos con mojibake.

---

## 2. Casos de Uso y Alcance Detallado

### UC-1: Registro Resiliente y Sincronización de Movimientos
- **Actor:** Usuario móvil.
- **Flujo Principal:**
  1. El usuario completa el formulario en `NuevaTransaccionScreen` (o escanea una factura en `SifenScannerScreen`).
  2. La app envía `proveedor_cliente` (por defecto "Varios" o el RUC/Razón Social escaneado), `nro_factura` ("S/N" o el detectado), `tasa_iva` ("10%", "5%" o "0%") y el tipo de comprobante sin caracteres corruptos (`"Física Legal"`, `"Virtual Legal"` o `"No Legal"`).
  3. El backend valida el payload contra `MovimientoCreate` sin errores y asienta el registro en `Libro_Diario` de Google Sheets.
  4. Si ocurre un error de cliente (`HTTP 400`), `SyncMovimientosWorker` no reintenta infinitamente, sino que marca el registro con fallo para intervención del usuario.

### UC-2: Integridad y Persistencia Bidireccional de Deudas (Obligaciones)
- **Actor:** Usuario móvil / Sistema contable.
- **Flujo Principal:**
  1. `Gamma_bot` incorpora `"Entidad"` en `ENCABEZADOS_OBLIGACIONES_MAESTRO` y devuelve en `GET /api/v1/obligaciones` los campos: `entidad`, `cuotas_totales`, `cuotas_restantes` y `dia_vencimiento`.
  2. `GammaMobile` actualiza su repositorio local de obligaciones utilizando un mecanismo de combinación (*upsert*) que preserva los datos locales en caso de discrepancias remotas.

### UC-3: Blindaje de Cuotas de Google Sheets API (Reducción del 95% de Llamadas)
- **Actor:** Sistema / Infraestructura.
- **Flujo Principal:**
  1. **En Android (`GammaMobile`):** `DashboardViewModel.onScreenVisible()` ejecuta `loadDashboard(forceRefresh = false, silent = true)`. Utiliza la caché local de 15 minutos en `gamma_cache` y los cálculos locales reactivos de `DashboardSummaryCalculator`. `forceRefresh = true` queda reservado exclusivamente para el gesto manual "Pull to Refresh" o inmediatamente después de guardar una transacción.
  2. **En Backend (`Gamma_bot`):** `SheetsRepository` implementa una caché en memoria RAM con TTL (3 a 5 minutos) para operaciones de solo lectura (`obtener_balance`, `get_all_movimientos`, `get_todas_obligaciones`, `obtener_presupuesto_base_completo`).
  3. **Invalidación Inmediata:** Cualquier mutación (`POST /movimientos`, `POST /obligaciones`, `POST /obligaciones/abonar`) invalida de inmediato la caché en memoria correspondiente.

### UC-4: Estabilización del Endpoint y Flujo de Marcación ("Marcar")
- **Actor:** Usuario móvil.
- **Flujo Principal:**
  1. El usuario pulsa "Marcar" en el Dashboard o en la pantalla de Asistencia.
  2. El backend auto-detecta dinámicamente el nombre de la hoja según el mes y año actual (`f"{mes_espanol} {ahora.year}"`, ej. `"Octubre 2026"`), sin depender de un archivo estático o fallar a `"Mayo 2026"`.
  3. El backend agrupa la lectura de filas/fechas para minimizar las llamadas a Sheets.
  4. Ante un rechazo por rate limit de Google Sheets (`HTTP 429`), el backend responde con un código claro y el cliente muestra un mensaje específico informando la saturación temporal del servicio en lugar de un error de desconexión genérico.

### UC-5: Flujo Contable Integrado de Abono de Obligaciones
- **Actor:** Usuario móvil.
- **Flujo Principal:**
  1. Al pulsar "Abonar Cuota", la app móvil invoca `POST /api/v1/obligaciones/abonar` enviando el `id_obligacion` y el `monto`.
  2. El backend amortiza el saldo en `Obligaciones_Maestro` e inserta automáticamente el egreso en `Libro_Diario` (`insert_movimiento_diario`), asegurando paridad contable en el balance mensual.

### UC-6: Ergonomía Táctil, Anti-Solapamiento y Corrección Visual (UI/UX)
- **Actor:** Usuario móvil.
- **Flujo Principal:**
  1. En `ObligacionesScreen.kt`, el `LazyColumn` utiliza `contentPadding.bottom = 152.dp`, permitiendo hacer scroll suficiente para que los botones de la última tarjeta queden completamente despejados del bloque de FABs.
  2. En `AvisosScreen.kt`, el `LazyColumn` utiliza `contentPadding.bottom = 136.dp`.
  3. En `DashboardScreen.kt`, se elimina el `Spacer(96.dp)` residual emitido fuera del contenedor.
  4. En `SifenScannerScreen.kt`, se aplica `Modifier.graphicsLayer { compositingStrategy = CompositingStrategy.Offscreen }` al Canvas de `ScannerOverlay`, garantizando un marco de visor transparente sobre la cámara.
  5. En `Theme.kt`, la barra de estado del sistema se sincroniza con el color de fondo de los `TopAppBar` (`MaterialTheme.colorScheme.background`) con iconos oscuros/claros adaptativos.

### UC-7: Persistencia Local Completa en Room y Previews de UI
- **Actor:** Desarrollador / Calidad.
- **Flujo Principal:**
  1. `AvisoDao.kt` incluye métodos `@Insert(onConflict = REPLACE) suspend fun insert(...)` y `@Query("DELETE FROM avisos WHERE id = :id") suspend fun deleteById(...)`, garantizando consistencia offline en `AvisoRepositoryImpl.kt`.
  2. Se generan componentes `@Preview` en Compose para los componentes modificados conforme a la regla de gobernanza de `GEMINI.md`.

---

## 3. Exclusiones Explícitas (No-Scope)

- **Migración a Base de Datos SQL Externa:** No se reemplazará Google Sheets por PostgreSQL/MySQL en esta fase; se optimizará el acceso mediante caché en memoria y batching.
- **Rediseño Completo de la Arquitectura de Navegación:** Se preserva el sistema actual de navegación por solapas (`ScreenBackStack`), corrigiendo únicamente paddings y solapamientos táctiles.
- **Soporte Multi-Usuario Simultáneo de Google Sheets:** El backend mantiene el modelo de service account con 1 hilo concurrente en PythonAnywhere.

---

## 4. Criterios de Aceptación y Validación

1. **Test Suite Android:** `./gradlew testDebugUnitTest` pasa al 100% con 0 fallos.
2. **Test Suite Backend:** `uv run pytest tests/test_mobile_api.py` pasa al 100% con los nuevos contratos.
3. **Prueba Empírica de Payload:** La serialización de `Movimiento` en Android es aceptada por `MovimientoCreate` de Pydantic sin arrojar `ValidationError`.
4. **Verificación de Cuotas:** 30 navegaciones consecutivas entre pantallas en Gamma Mobile no generan más de 2 peticiones a Google Sheets gracias a las capas de caché de cliente y servidor.
5. **Ergonomía:** Los botones "Abonar Cuota", "Aprobar" y "Cancelar" del último ítem de `ObligacionesScreen` son 100% visibles y accionables sin interferencia de los FABs.
