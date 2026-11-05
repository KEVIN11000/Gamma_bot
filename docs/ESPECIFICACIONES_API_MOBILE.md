# Especificación de Contratos y Requerimientos de API: Gamma Mobile ↔ Gamma Backend

**Versión:** 2.0.0 (Alineación Integral Core Bot & API v2)  
**Fecha:** Noviembre 2026  
**Cliente:** Android (`GammaMobile` — Jetpack Compose, Retrofit, Kotlinx Coroutines, Room, WorkManager, Firebase Cloud Messaging)  
**Servidor:** Python / Flask (`Gamma_bot` — Blueprints, Pydantic, GSpread / Google Sheets, SQLite LocalRepository)  
**Host de Producción:** `https://kevin11000.pythonanywhere.com/api/v1/`

---

## 1. Arquitectura General de Comunicación

### 1.1 Protocolo y Convenciones
- **Protocolo:** HTTPS / REST sobre JSON.
- **Base URL:** `https://kevin11000.pythonanywhere.com/api/v1/` (configurable dinámicamente en tiempo de ejecución vía `DynamicBaseUrlInterceptor`).
- **Autenticación:** Header estándar obligatorio `X-API-KEY: <token>` inyectado por `ApiKeyInterceptor`. Blindaje fail-closed activo en producción.
- **Moneda:** Guaraní Paraguayo (₲ / PYG). Todos los importes monetarios se manejan como **enteros sin decimales** (`Long` en Kotlin, `int` en Python).
- **Zonas Horarias:** Todas las marcas temporales y fechas deben expresarse en la zona horaria oficial de Paraguay (`America/Asuncion`, UTC-3 o UTC-4 según horario de verano/invierno). Formato estándar de fecha: `DD/MM/YYYY` o `YYYY-MM-DD` según el contrato.
- **Formato Estándar de Errores (`HTTP 4xx / 5xx`):**
```json
{
  "error": true,
  "code": "VALIDATION_ERROR",
  "mensaje": "Descripción legible para usuario o registro de auditoría",
  "detalles": null
}
```

---

## 2. Catálogo Detallado de Endpoints por Módulo

---

### Módulo A: Monitoreo, Salud e Hidratación Global

#### A.1 Chequeo de Salud del Servidor
- **Método / Ruta:** `GET health`
- **Headers:** `X-API-KEY`
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "status": "ok",
  "sheets": true,
  "avisos": true,
  "version_api": "2.0.0",
  "latest_app_version": "0.0.12",
  "latest_app_version_code": 12,
  "download_url": "https://github.com/KEVIN11000/Gamma_Mobile/releases/download/v0.0.12/app-release.apk"
}
```

#### A.2 Hidratación Global Atómica (Bootstrap)
- **Método / Ruta:** `GET bootstrap`
- **Uso en Mobile:** Unifica el arranque de la app en un solo round-trip al abrir la pantalla de bienvenida, alimentando el almacenamiento local Room.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "resumen_financiero": {
    "margen_libre": 2500000,
    "saldo_acumulado": 1431300,
    "posicion_iva": 125000,
    "es_debito_fiscal": false
  },
  "estado_asistencia_hoy": {
    "fecha": "04/11/2026",
    "estado": "TRABAJANDO",
    "hora_entrada": "08:02",
    "hora_salida": null,
    "puede_marcar_entrada": false,
    "puede_marcar_salida": true
  },
  "clima": {
    "temperatura": 24.5,
    "condicion": "Lluvia ligera",
    "llevar_paraguas": true,
    "mensaje": "Se prevén precipitaciones en Asunción. Llevá paraguas ☔."
  },
  "proximos_avisos": [],
  "proximos_vencimientos": []
}
```

#### A.3 Logs del Sistema
- **Método / Ruta:** `GET sistema/logs`
- **Headers:** `X-API-KEY`
- **Respuesta Exitosa (`HTTP 200 OK`):** Lista cronológica de logs de depuración.

---

### Módulo B: Dashboard y Proyecciones Financieras

#### B.1 Resumen Financiero para Dashboard
- **Método / Ruta:** `GET dashboard/summary`
- **Uso en Mobile:** Alimenta las tarjetas superiores de `DashboardScreen`.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "margen_libre": 2500000,
  "saldo_acumulado": 1431300,
  "posicion_iva": 125000,
  "es_debito_fiscal": false
}
```
- **Semántica de Campos:**
  - `margen_libre`: Saldo proyectado libre de compromisos de deuda del mes corriente (`ingresos_base - gastos_fijos - cuotas_deudas`).
  - `saldo_acumulado`: Saldo real disponible en caja/bancos (`saldo_inicial + total_ingresos - total_gastos`).
  - `posicion_iva`: Monto neto de IVA acumulado del mes.
  - `es_debito_fiscal`: `true` si se debe pagar IVA a DNIT; `false` si es crédito fiscal a favor.

#### B.2 Proyector de Flujo de Caja a 30 Días
- **Método / Ruta:** `GET proyecciones/flujo-caja`
- **Uso en Mobile:** Alimenta el gráfico interactivo de liquidez futura en `ProyeccionesScreen`.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "saldo_actual": 1431300,
  "dias_proyectados": 30,
  "curva_diaria": [
    {
      "fecha": "2026-11-04",
      "dia": 4,
      "saldo_proyectado": 1431300,
      "es_critico": false,
      "eventos": []
    },
    {
      "fecha": "2026-11-10",
      "dia": 10,
      "saldo_proyectado": 781300,
      "es_critico": false,
      "eventos": ["Vencimiento Banco Familiar (-650.000 ₲)"]
    }
  ],
  "dias_criticos": [],
  "saldo_final_estimado": 1950000
}
```

---

### Módulo C: Presupuesto Base, Gastos Fijos y Techos

#### C.1 Listar Gastos Fijos y Salario Base
- **Método / Ruta:** `GET presupuesto/fijos`
- **Uso en Mobile:** Alimenta la vista `PresupuestoScreen` con el desglose de costos fijos por categoría y el ingreso de referencia mensual.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "salario_base": 6500000,
  "total_gastos_fijos": 2850000,
  "categorias": {
    "Vivienda": [
      {"concepto": "Alquiler", "monto": 1500000, "concepto_id": "Alquiler"},
      {"concepto": "Expensas", "monto": 250000, "concepto_id": "Expensas"}
    ],
    "Servicios": [
      {"concepto": "Internet Fibra", "monto": 180000, "concepto_id": "Internet_Fibra"},
      {"concepto": "Electricidad Ande", "monto": 320000, "concepto_id": "Electricidad_Ande"}
    ],
    "Seguros": [
      {"concepto": "Seguro Médico", "monto": 600000, "concepto_id": "Seguro_Médico"}
    ]
  }
}
```

#### C.2 Actualizar Monto de un Gasto Fijo
- **Método / Ruta:** `PUT presupuesto/fijos/{concepto}`
- **Payload (`JSON`):**
```json
{
  "nuevo_monto": 1600000
}
```
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "status": "ok",
  "concepto": "Alquiler",
  "nuevo_monto": 1600000,
  "mensaje": "Monto de gasto fijo actualizado correctamente."
}
```

#### C.3 Agregar Nuevo Gasto Fijo
- **Método / Ruta:** `POST presupuesto/fijos`
- **Payload (`JSON`):**
```json
{
  "categoria": "Servicios",
  "concepto": "Suscripción Cloud",
  "monto": 85000
}
```
- **Respuesta Exitosa (`HTTP 201 Created`):**
```json
{
  "status": "ok",
  "concepto": "Suscripción Cloud",
  "categoria": "Servicios",
  "monto": 85000,
  "mensaje": "Gasto fijo registrado con éxito en Presupuesto_Base."
}
```

#### C.4 Actualizar Salario / Ingreso Base
- **Método / Ruta:** `PUT presupuesto/salario-base`
- **Payload (`JSON`):**
```json
{
  "nuevo_salario": 7000000
}
```
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "status": "ok",
  "nuevo_salario": 7000000,
  "mensaje": "Salario base actualizado en el presupuesto."
}
```

#### C.5 Resumen de Techos y Alertas Presupuestarias
- **Método / Ruta:** `GET presupuesto/techos`
- **Uso en Mobile:** Alimenta las barras de progreso "Gasto vs Presupuesto" y genera advertencias preventivas locales si una categoría superó el umbral.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
[
  {
    "categoria": "Supermercado",
    "limite_mensual": 1500000,
    "consumido": 1250000,
    "porcentaje": 83.3,
    "umbral_alerta": 80,
    "alerta_emitida": true,
    "estado": "ALERTA",
    "mensaje": "Has consumido el 83.3% del presupuesto asignado a Supermercado."
  },
  {
    "categoria": "Combustible",
    "limite_mensual": 600000,
    "consumido": 250000,
    "porcentaje": 41.6,
    "umbral_alerta": 80,
    "alerta_emitida": false,
    "estado": "NORMAL",
    "mensaje": "Dentro del límite presupuestario."
  }
]
```

---

### Módulo D: Movimientos, Libro Diario e IA Transaccional

#### D.1 Listado de Movimientos
- **Método / Ruta:** `GET movimientos`
- **Parámetros Opcionales:** `?mes=11&anio=2026&limite=50`
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
[
  {
    "id": "mov-2026-11-04-001",
    "fecha": "04/11/2026",
    "tipo": "Gasto",
    "categoria": "Combustible",
    "total": 250000,
    "comprobante": "Virtual Legal",
    "proveedor_cliente": "Petrobras",
    "nro_factura": "001-001-0004521",
    "tasa_iva": "10%",
    "client_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
]
```

#### D.2 Registrar Nuevo Movimiento
- **Método / Ruta:** `POST movimientos`
- **Payload (`JSON`):**
```json
{
  "client_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "fecha": "04/11/2026",
  "tipo": "Gasto",
  "categoria": "Supermercado",
  "total": 185000,
  "comprobante": "Virtual Legal",
  "proveedor_cliente": "Superseis",
  "nro_factura": "001-002-1234567",
  "tasa_iva": "10%"
}
```
- **Requisitos de Backend:**
  - Soporte de alias: Acepta `"tipo"` o `"movimiento"`, `"total"` o `"monto"`, `"proveedor_cliente"` o `"concepto"`.
  - **Idempotencia:** Si se recibe `client_id` registrado en las últimas 24h, devuelve `HTTP 200 OK` sin duplicar.
  - **Invalidación Reactiva:** Ejecuta `_sheets_cache.clear()` tras la inserción.

#### D.3 Parser Conversacional NLP Ultrarrápido (<5ms)
- **Método / Ruta:** `POST movimientos/parse`
- **Uso en Mobile:** Parseo en tiempo real mientras el usuario tipea o dicta un gasto.
- **Payload (`JSON`):** `{"texto": "Supermercado 150000 factura legal"}`
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "tipo": "Gasto",
  "categoria": "Supermercado",
  "total": 150000,
  "comprobante": "Virtual Legal",
  "proveedor_cliente": "Supermercado",
  "nro_factura": "S/N",
  "tasa_iva": "10%",
  "tiempo_ms": 1.8
}
```

#### D.4 Interpretación Semántica con Inteligencia Artificial
- **Método / Ruta:** `POST ia/interpretar`
- **Payload:** `{"texto": "Almuerzo en Biggie por 35000 factura legal"}`
- **Respuesta Exitosa:**
```json
{
  "id": "",
  "fecha": "04/11/2026",
  "tipo": "Gasto",
  "tipo_movimiento": "Gasto",
  "categoria": "Alimentación",
  "total": 35000,
  "comprobante": "Física Legal",
  "proveedor_cliente": "Biggie Express",
  "nro_factura": "S/N",
  "tasa_iva": "10%"
}
```

#### D.5 Escaneo OCR de Comprobantes Físicos
- **Método / Ruta:** `POST movimientos/ocr`
- **Content-Type:** `multipart/form-data` (archivo `file` JPG/PNG).
- **Respuesta:** Objeto `Movimiento` estructurado.

#### D.6 Descarga de Reportes del Libro Diario
- **Métodos / Rutas:**
  - `GET reportes/financiero/excel?mes=11&anio=2026`
  - `GET reportes/financiero/pdf?mes=11&anio=2026`
- **Headers:** `X-API-KEY`
- **Retorno:** Stream de archivo binario descargable.

---

### Módulo E: Obligaciones, Deudas y Proyectos de Inversión

#### E.1 Listar Obligaciones
- **Método / Ruta:** `GET obligaciones`
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
[
  {
    "id": "DEUDA-001",
    "nombre": "Préstamo Banco Familiar",
    "entidad": "Banco Familiar",
    "tipo": "Préstamo",
    "monto_inicial": 15000000,
    "saldo_actual": 8200000,
    "cuota_referencia_gs": 650000,
    "cuotas_totales": 24,
    "cuotas_restantes": 13,
    "dia_vencimiento": 10,
    "fecha_inicio": "2025-10-10",
    "estado": "Activo",
    "observaciones": "Débito automático"
  }
]
```

#### E.2 CRUD de Obligaciones
- **Crear:** `POST obligaciones`
- **Editar:** `PUT obligaciones/{id}`
- **Eliminar:** `DELETE obligaciones/{id}`

#### E.3 Abonar Cuota o Pago Extraordinario
- **Método / Ruta:** `POST obligaciones/abonar`
- **Payload (`JSON`):**
```json
{
  "id_obligacion": "DEUDA-001",
  "monto": 650000,
  "nro_factura": "001-001-0098765",
  "tasa_iva": "10%"
}
```
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "status": "ok",
  "id_obligacion": "DEUDA-001",
  "saldo_actual": 7550000,
  "estado": "Activo"
}
```

#### E.4 Cronograma de Vencimientos y Deuda Foco
- `GET obligaciones/vencimientos` -> Lista de compromisos del mes ordenados cronológicamente con días restantes.
- `GET obligaciones/foco?criterio={saldo|prioridad}` -> Retorna la deuda prioritaria a amortizar (Bola de Nieve o Avalancha) con estructura plana en raíz.

#### E.5 Simulador de Proyectos de Inversión y Capital
- **Método / Ruta:** `POST proyectos/simular`
- **Uso en Mobile:** Permite al usuario evaluar la viabilidad de una compra grande o crédito antes de comprometerse.
- **Payload (`JSON`):**
```json
{
  "concepto": "Notebook Profesional",
  "monto": 6000000,
  "meses": 12
}
```
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "id_proyecto": "PRY-8A2F1B",
  "concepto": "Notebook Profesional",
  "monto_total": 6000000,
  "meses": 12,
  "cuota_mensual": 500000,
  "ingreso_base": 6500000,
  "gastos_fijos": 2850000,
  "cuotas_actuales": 1100000,
  "margen_libre_post_proyecto": 2050000,
  "dti_resultante": 24.6,
  "diagnostico": "Viable",
  "semaforo": "VERDE",
  "mensaje": "Tu salud financiera soporta esta nueva cuota cómodamente."
}
```

#### E.6 Aprobación Formal de Proyecto
- **Método / Ruta:** `POST proyectos/{id_proyecto}/aprobar`
- **Efecto:** Convierte el proyecto simulado en una obligación activa real en `Obligaciones_Maestro`.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "status": "ok",
  "id_proyecto": "PRY-8A2F1B",
  "estado": "Activo",
  "mensaje": "Proyecto aprobado e incorporado como obligación activa."
}
```

---

### Módulo F: Asistencia, Control Laboral y Materias Pedagógicas

#### F.1 Estado Diario de Jornada (Lectura de Inicio)
- **Método / Ruta:** `GET asistencia/estado-hoy`
- **Uso en Mobile:** Determina el estado del reloj en Android sin mutar datos.
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "fecha": "04/11/2026",
  "estado": "TRABAJANDO",
  "hora_entrada": "08:02",
  "hora_salida": null,
  "minutos_transcurridos": 195,
  "tiempo_transcurrido_formato": "3h 15m",
  "puede_marcar_entrada": false,
  "puede_marcar_salida": true,
  "es_feriado_o_descanso": false
}
```

#### F.2 Marcar Entrada / Salida
- **Método / Ruta:** `POST asistencia/marcar`
- **Payload:** `{"modo": "normal"}` o `{"modo": "directo"}`
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "tipo": "entrada",
  "hora": "08:02",
  "mensaje": "✅ Entrada registrada a las 08:02",
  "planilla": "Horas_Noviembre_2026",
  "fila": 14,
  "confirmado_en_planilla": true
}
```
- **Respuesta ante Marcación Previa (Evitar HTTP 400):** Si ya marcó, retorna `HTTP 200 OK` con `"tipo": "info"` para evitar errores falsos en el worker móvil.

#### F.3 Materias Pedagógicas
- `GET asistencia/materias`: Lista catálogo de materias cátedra activas.
- `POST asistencia/materia`: Registra cátedra con payload `{"materia": "Física Aplicada", "horas": 2}`.

#### F.4 Analíticas, Cierres y Descarga de Reportes
- `GET asistencia/periodos`: Lista hojas de asistencia históricas.
- `GET asistencia/analiticas?hoja={nombre_hoja}`: Devuelve horas trabajadas, devengado en guaraníes, horas extras y promedio diario.
- `GET asistencia/reporte/excel` y `GET asistencia/reporte/pdf`: Descarga de reportes laborales con parámetros `descuento`, `saldo_anterior` e `incluir_iva`.
- `POST asistencia/sync`: Sincronización bidireccional forzada entre Room/SQLite y Google Sheets.

---

### Módulo G: Avisos, Recordatorios y Contexto Ambiental

#### G.1 CRUD de Avisos
- `GET avisos`
- `POST avisos`
- `PUT avisos/{id}`
- `DELETE avisos/{id}`
- `POST ia/interpretar/aviso`: Parseo por lenguaje natural de recordatorios recurrentes.

#### G.2 Tarjeta Climática y Recomendación de Paraguas
- **Método / Ruta:** `GET clima`
- **Respuesta Exitosa (`HTTP 200 OK`):**
```json
{
  "temperatura": 24.5,
  "humedad": 78,
  "condicion": "Lluvia moderada",
  "llevar_paraguas": true,
  "mensaje": "Precipitaciones detectadas en Asunción. Llevá paraguas ☔.",
  "fuente": "Open-Meteo"
}
```

#### G.3 Notificaciones Push FCM
- `POST dispositivos/registrar`: Registra el token FCM del teléfono para recibir notificaciones push en segundo plano.
- `POST dispositivos/notificar`: Despacho selectivo o global de avisos push.

---

### Módulo H: Cierres Contables y Laborales

#### H.1 Ejecutar Cierre de Período
- **Método / Ruta:** `POST cierres/ejecutar`
- **Payload (`JSON`):**
```json
{
  "tipo": "horas",
  "hoja": "Horas_Octubre_2026",
  "aplicar_descuento": false,
  "descuento": 0,
  "incluir_iva": true
}
```
*(También admite `tipo: "deudas"` para disparar el rollover mensual de cuotas).*

#### H.2 Historial de Cierres y Descargas
- `GET cierres`: Lista cierres históricos con montos y links de descarga.
- `GET cierres/reportes/{filename}`: Descarga autenticada del PDF de cierre.

---

### Módulo I: Soporte e Incidencias Técnicas

#### I.1 Gestión de Tickets
- `GET soporte/tickets`
- `POST soporte/tickets`: Creación de reporte de bug o consulta desde la app.
- `PATCH soporte/tickets/{id}`: Actualización de estado del ticket.

---

## 3. Estado de Disponibilidad de Endpoints en Producción (v2.0.0)

| Endpoint | Módulo | Estado en Producción | Acción Backend Requerida |
|---|---|---|---|
| `GET health` | Sistema | ✅ Disponible | Ninguna |
| `GET bootstrap` | Sistema | ⏳ Pendiente | Implementar endpoint unificado |
| `GET dashboard/summary` | Finanzas | ✅ Disponible | Corregir cálculo de `flujo_neto` |
| `GET proyecciones/flujo-caja` | Finanzas | ✅ Disponible | Ninguna |
| `GET presupuesto/fijos` | Presupuesto | ⏳ Pendiente | Implementar Blueprint `routes_presupuesto.py` |
| `PUT presupuesto/fijos/{concepto}` | Presupuesto | ⏳ Pendiente | Implementar Blueprint `routes_presupuesto.py` |
| `POST presupuesto/fijos` | Presupuesto | ⏳ Pendiente | Implementar Blueprint `routes_presupuesto.py` |
| `PUT presupuesto/salario-base` | Presupuesto | ⏳ Pendiente | Implementar Blueprint `routes_presupuesto.py` |
| `GET presupuesto/techos` | Presupuesto | ⏳ Pendiente | Implementar Blueprint `routes_presupuesto.py` |
| `GET movimientos` | Transacciones | ✅ Disponible | Ninguna |
| `POST movimientos` | Transacciones | ✅ Disponible | Ninguna |
| `POST movimientos/parse` | Transacciones | ✅ Disponible | Ninguna |
| `POST movimientos/ocr` | Transacciones | ✅ Disponible | Ninguna |
| `GET reportes/financiero/excel` | Reportes | ⏳ Pendiente | Exponer endpoint de Libro Diario |
| `GET reportes/financiero/pdf` | Reportes | ⏳ Pendiente | Exponer endpoint de Libro Diario |
| `GET obligaciones` | Deudas | ✅ Disponible | Ninguna |
| `POST obligaciones` | Deudas | ✅ Disponible | Ninguna |
| `POST obligaciones/abonar` | Deudas | ✅ Disponible | Ninguna |
| `GET obligaciones/vencimientos` | Deudas | ✅ Disponible | Ninguna |
| `GET obligaciones/foco` | Deudas | ✅ Disponible | Ninguna |
| `POST obligaciones/proyectar-capacidad` | Deudas | ✅ Disponible | Ninguna |
| `POST proyectos/simular` | Proyectos | ⏳ Pendiente | Incorporar persistencia de ID Simulado |
| `POST proyectos/{id}/aprobar` | Proyectos | ⏳ Pendiente | Implementar aprobación de proyecto |
| `GET asistencia/estado-hoy` | Asistencia | ⏳ Pendiente | Implementar consulta rápida de jornada |
| `POST asistencia/marcar` | Asistencia | ✅ Disponible | Ninguna |
| `GET asistencia/materias` | Asistencia | ✅ Disponible | Ninguna |
| `POST asistencia/materia` | Asistencia | ✅ Disponible | Ninguna |
| `GET asistencia/analiticas` | Asistencia | ✅ Disponible | Ninguna |
| `GET asistencia/reporte/*` | Asistencia | ✅ Disponible | Ninguna |
| `POST asistencia/sync` | Asistencia | ✅ Disponible | Ninguna |
| `GET/POST/PUT/DELETE avisos` | Avisos | ✅ Disponible | Ninguna |
| `GET clima` | Ambiental | ✅ Disponible | Ninguna |
| `POST dispositivos/registrar` | Push FCM | ✅ Disponible | Ninguna |
| `POST cierres/ejecutar` | Cierres | ✅ Disponible | Habilitar `tipo="deudas"` |
| `GET soporte/tickets` | Soporte | ✅ Disponible | Ninguna |
