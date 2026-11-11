# Guía de Integración para Gamma Mobile (Android) — Backend v2.1.4

> **Audiencia:** Desarrolladores de Gamma Mobile (Kotlin, Jetpack Compose, Retrofit, Room, Coroutines).  
> **Versión de Backend:** `v2.1.4`  
> **Base URL:** `https://kevin11000.pythonanywhere.com/api/v1/`  
> **Fecha de Publicación:** 2026-11-11  

---

## 1. Resumen de Novedades y Capacidades para la App

La versión **v2.1.4** del backend de Gamma introduce capacidades de auto-descubrimiento, paridad presupuestaria completa y reportes optimizados para facturación que deben ser asumidos por el cliente Android:

1. **Auto-Descubrimiento de API (`GET /capacidades`)**: Permite a la app consultar al iniciar qué endpoints y funciones están activos en el servidor, adaptando la UI dinámicamente (*Feature Toggles*).
2. **Gestión Completa de Presupuesto Base**:
   - Borrado de gastos fijos (`DELETE /presupuesto/fijos/{concepto}`).
   - Establecimiento de techos variables (`PUT /presupuesto/techos/{categoria}`).
   - Actualización de salario base (`PUT /presupuesto/salario-base`).
3. **Obligaciones Libres de Campos Obsoletos**:
   - Los campos legacy `Cuotas` y `Event_ID` ya **no son requeridos** por el backend. Los DTOs de Android pueden omitirlos con seguridad.
4. **Descarga de Reportes de Asistencia (PDF A4 y Excel .xlsx)**:
   - El PDF ahora está calibrado para entrar **100% en una sola hoja A4** para períodos de hasta 31 días.
   - Las planillas Excel cuentan con fórmulas y etiquetas de liquidación estandarizadas (`Horas del mes`, `Monto por hora`, `Total Monto por Horas`, `IVA 10%`, `TOTAL IVA INCLUIDO`, `TOTAL FACTURA`).

---

## 2. Auto-Descubrimiento de Capacidades (`GET /api/v1/capacidades`)

### 2.1 Por qué y cómo usarlo en Android
En lugar de codificar de forma rígida qué botones mostrar o arriesgar caídas con errores HTTP 404 si el backend se actualiza a distinto ritmo que la APK, la app debe consultar `/capacidades` en el arranque (junto al flujo de `/bootstrap`) y guardar las banderas en un StateFlow o DataStore.

### 2.2 Modelos Kotlin (DTOs)

```kotlin
package com.gamma.mobile.data.model.capacidades

import com.google.gson.annotations.SerializedName

data class CapacidadesResponse(
    @SerializedName("version_api")
    val versionApi: String,
    @SerializedName("total_rutas")
    val totalRutas: Int,
    @SerializedName("modulos")
    val modulos: List<String>,
    @SerializedName("capacidades_clave")
    val capacidadesClave: Map<String, Boolean>,
    @SerializedName("rutas")
    val rutas: List<RutaEndpointInfo>
)

data class RutaEndpointInfo(
    @SerializedName("modulo")
    val modulo: String,
    @SerializedName("ruta")
    val ruta: String,
    @SerializedName("metodos")
    val metodos: List<String>,
    @SerializedName("nombre_endpoint")
    val nombreEndpoint: String,
    @SerializedName("descripcion")
    val descripcion: String,
    @SerializedName("autenticacion")
    val autenticacion: Boolean,
    @SerializedName("parametros")
    val parametros: List<String> = emptyList()
)
```

### 2.3 Banderas Clave para Feature Toggles (`capacidades_clave`)

| Flag Booleano | Componente UI / Pantalla en Gamma Mobile | Comportamiento en la App |
|---|---|---|
| `presupuesto_fijos_delete` | `PresupuestoScreen` (Gastos Fijos) | Habilita el icono de basurero / deslizar para eliminar un gasto fijo. |
| `presupuesto_techos_put` | `PresupuestoScreen` (Límites Variables) | Permite abrir el diálogo de edición del techo mensual por categoría. |
| `asistencia_excel_export` | `AsistenciaScreen` / Historial | Muestra la opción *"Descargar Planilla Excel (.xlsx)"*. |
| `asistencia_pdf_a4_optimizado` | `AsistenciaScreen` / Historial | Informa al usuario que el PDF exportado es de 1 sola carátula imprimible A4. |
| `obligaciones_deuda_foco` | `ObligacionesScreen` | Despliega la tarjeta superior de la Deuda Foco recomendada (Bola de Nieve/Avalancha). |
| `obligaciones_abonar_post` | `ObligacionesScreen` | Activa el botón de abono rápido de cuotas con asiento automático en caja. |

---

## 3. Módulo de Presupuesto en Jetpack Compose

### 3.1 Contratos Retrofit

```kotlin
interface PresupuestoApi {
    @GET("presupuesto/fijos")
    suspend fun obtenerGastosFijos(): Response<PresupuestoFijosResponse>

    @POST("presupuesto/fijos")
    suspend fun crearGastoFijo(@Body request: GastoFijoCreateRequest): Response<ApiResponse<Unit>>

    @PUT("presupuesto/fijos/{concepto}")
    suspend fun actualizarGastoFijo(
        @Path("concepto") concepto: String,
        @Body request: GastoFijoUpdateRequest
    ): Response<ApiResponse<Unit>>

    @DELETE("presupuesto/fijos/{concepto}")
    suspend fun eliminarGastoFijo(
        @Path("concepto") concepto: String
    ): Response<ApiResponse<Unit>>

    @PUT("presupuesto/salario-base")
    suspend fun actualizarSalarioBase(
        @Body request: SalarioBaseUpdateRequest
    ): Response<ApiResponse<Unit>>

    @GET("presupuesto/techos")
    suspend fun obtenerTechosPresupuestarios(): Response<TechosResponse>

    @PUT("presupuesto/techos/{categoria}")
    suspend fun actualizarTechoPresupuestario(
        @Path("categoria") categoria: String,
        @Body request: TechoUpdateRequest
    ): Response<ApiResponse<Unit>>
}
```

### 3.2 DTOs de Petición

```kotlin
data class TechoUpdateRequest(
    @SerializedName("monto_limite")
    val montoLimite: Long,
    @SerializedName("umbral_alerta_pct")
    val umbralAlertaPct: Int = 80
)

data class SalarioBaseUpdateRequest(
    @SerializedName("nuevo_salario")
    val nuevoSalario: Long
)

data class GastoFijoCreateRequest(
    @SerializedName("categoria")
    val categoria: String,
    @SerializedName("concepto")
    val concepto: String,
    @SerializedName("monto")
    val monto: Long
)
```

### 3.3 Experiencia de Usuario Recomendada en Compose
* **Gastos Fijos:** Mostrar lista agrupada por categorías (`Vivienda`, `Servicios`, `Suscripciones`, etc.). Cada ítem debe presentar un botón o menú contextual para:
  - Editar monto (`PUT /presupuesto/fijos/{concepto}`).
  - Eliminar concepto (`DELETE /presupuesto/fijos/{concepto}`) con un `AlertDialog` de confirmación: *"¿Eliminar este gasto fijo? El cálculo de tu Margen Libre se actualizará automáticamente"*.
* **Techos Variables:** Mostrar tarjetas de progreso con indicador porcentual ($Gastado / Límite$). Si el consumo supera el 80% mostrar color Ámbar; si supera el 100% mostrar Rojo. El botón de lápiz abre el modal para invocar `actualizarTechoPresupuestario`.

---

## 4. Módulo de Obligaciones (Deudas) Saneado

### 4.1 Simplificación de Esquemas en la App
El backend ahora maneja defensivamente el formato de 17 columnas de Google Sheets. En Android:
* **No enviar `cuotas` ni `event_id`**: No es necesario incluir estos campos en `ObligacionCreateRequest`.
* **Esquema de Alta de Deuda Recomendado**:

```kotlin
data class ObligacionCreateRequest(
    @SerializedName("acreedor")
    val acreedor: String,
    @SerializedName("concepto")
    val concepto: String,
    @SerializedName("monto_total")
    val montoTotal: Long,
    @SerializedName("saldo_pendiente")
    val saldoPendiente: Long,
    @SerializedName("monto_cuota")
    val montoCuota: Long,
    @SerializedName("cuotas_totales")
    val cuotasTotales: Int,
    @SerializedName("cuotas_pagadas")
    val cuotasPagadas: Int = 0,
    @SerializedName("dia_vencimiento")
    val diaVencimiento: Int,
    @SerializedName("tasa_interes")
    val tasaInteres: Double = 0.0,
    @SerializedName("tipo_deuda")
    val tipoDeuda: String = "Fija"
)
```

---

## 5. Módulo de Asistencia & Descarga de Reportes

### 5.1 Endpoints de Descarga

```kotlin
interface AsistenciaReportesApi {
    @Streaming
    @GET("asistencia/reporte/pdf")
    suspend fun descargarReportePdf(
        @Query("hoja") hoja: String? = null,
        @Query("descuento") descuento: Long = 0,
        @Query("saldo_anterior") saldoAnterior: Long = 0,
        @Query("incluir_iva") incluirIva: Boolean = true
    ): Response<ResponseBody>

    @Streaming
    @GET("asistencia/reporte/excel")
    suspend fun descargarReporteExcel(
        @Query("hoja") hoja: String? = null,
        @Query("descuento") descuento: Long = 0,
        @Query("saldo_anterior") saldoAnterior: Long = 0,
        @Query("incluir_iva") incluirIva: Boolean = true
    ): Response<ResponseBody>
}
```

### 5.2 Descarga y Visualización en Android
* Guardar el `ResponseBody.byteStream()` en el directorio de `Downloads` o caché privada de la app mediante `FileProvider`.
* Abrir el archivo utilizando un `Intent(Intent.ACTION_VIEW)` con `application/pdf` o `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
* El PDF resultante cuenta con la garantía de **1 sola página A4**, facilitando su envío directo por WhatsApp o correo al cliente/empleador.

---

## 6. Mapeo de Códigos de Error Estándar

| Código HTTP | `error.code` | Causa | Acción Recomendada en Gamma Mobile |
|---|---|---|---|
| `401 Unauthorized` | `UNAUTHORIZED` | Cabecera `X-API-KEY` faltante o inválida. | Redirigir a pantalla de configuración / ingreso de clave. |
| `400 Bad Request` | `VALIDATION_ERROR` | Error en campos de payload (ej. monto negativo). | Marcar los `OutlinedTextField` en rojo con el mensaje de error devuelto. |
| `404 Not Found` | `NOT_FOUND` | Concepto fijo o categoría no encontrada. | Notificar por Snackbar y refrescar la lista local. |
| `500 Server Error` | `INTERNAL_ERROR` | Fallo de conexión con Google Sheets u otra falla no capturada. | Mostrar mensaje amigable de reintento offline. |

---

## 7. Checklist de Implementación en Gamma Mobile

- [ ] Implementar `CapacidadesResponse` y llamada a `GET /api/v1/capacidades` en el flujo de inicialización.
- [ ] Enlazar `capacidades_clave` al estado global de la app para condicionar las acciones de UI.
- [ ] Construir la pantalla `PresupuestoScreen` con integración a los endpoints de fijos y techos variables.
- [ ] Actualizar el repositorio de deudas eliminando dependencias de `cuotas` y `event_id`.
- [ ] Incorporar botones de acción para descarga de PDF oficial y planilla Excel desde el historial de asistencia.
