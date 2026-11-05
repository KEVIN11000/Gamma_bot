# 🤖 GAMMA — Backend Omnicanal & API REST (v2.1.0)

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-480%20passing-brightgreen.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Architecture](https://img.shields.io/badge/architecture-hexagonal%20%2F%20ports%20%26%20adapters-orange.svg)](src/)

**GAMMA** es un backend omnicanal de gestión financiera estratégica, control de asistencia laboral, proyección de liquidez y agendamiento inteligente. Provee una **API REST modular** (`/api/v1`) de alto rendimiento para el cliente móvil **Gamma Mobile** (Android), integración bidireccional con **Telegram**, **WhatsApp** y servicios de **Google Cloud** (Google Sheets, Google Calendar y Gemini 2.5).

Diseñado para operar 24/7 en servidores cloud como **PythonAnywhere** con persistencia dual: base de datos local SQLite con modo WAL (latencia $<15$ ms) y réplica periódica en Google Sheets.

---

## 🌟 Novedades Principales en la Versión 2.0.0

* **Arquitectura Hexagonal & Omnicanal:** Despachador unificado (`NotificationDispatcher`) con puerto canónico `INotificationPort` que enruta notificaciones de manera agnóstica a través de **Telegram**, **WhatsApp**, **Push Móvil** o adaptadores simulados.
* **Proyector de Flujo de Caja a 30 Días:** Motor algorítmico (`CashFlowProjector`) que simula día por día la liquidez a 30 días calendario, imputando compromisos bancarios de `Obligaciones_Maestro`, consumo variable diario e ingresos esperados, detectando automáticamente fechas críticas de iliquidez.
* **Alertas Presupuestarias Proactivas:** Monitoreo en tiempo real del techo presupuestario con advertencias inmediatas y ventana de enfriamiento (*cooldown*) de 24 horas por categoría para evitar spam.
* **Parser Financiero Conversacional (NLP):** Motor determinista (`FinanceNLParser`) con regex de alto rendimiento para extraer montos (Gs., USD, multiplicadores `k`/`M`), tipo de movimiento, comercios paraguayos reconocidos y categorías canónicas en $<5$ ms.
* **Canal WhatsApp Asíncrono:** Webhook desacoplado con encolado en `cola.db` SQLite (WAL), saneamiento E.164 y soporte para Evolution API.
* **Notificaciones Push y Registro de Dispositivos:** Gestión idempotente de tokens móviles y emisión push local/FCM para clientes Gamma Mobile.
* **Hardening y Rate Limiting Centralizado:** Limitación de tasa de 60 req/min por IP real (`X-Forwarded-For`), filtro contra ráfagas y límite de carga útil de 64 KB (`HTTP 413`).
* **Sincronización Bidireccional:** Endpoint para sincronizar registros locales de SQLite con Google Sheets y viceversa (`POST /api/v1/sincronizar`).

---

## 📱 Contratos REST API Móvil (`/api/v1`)

Todos los endpoints (salvo el webhook público protegido por secreto) requieren autenticación mediante cabecera HTTP:
```http
X-API-KEY: <tu-clave-api>
```
*(También se admite `Authorization: Bearer <tu-clave-api>`)*.

### Catálogo Completo de Endpoints

| Módulo | Método | Endpoint | Descripción | Body / Query Params |
|---|---|---|---|---|
| **Sistema** | `GET` | `/api/v1/health` | Estado del backend, uptime y versión activa. | Ninguno |
| **Sistema** | `GET` | `/api/v1/sistema/logs` | Logs de servidor paginados en orden cronológico inverso. | `?limit=50&offset=0` |
| **Dashboard** | `GET` | `/api/v1/dashboard/summary` | Saldo actual, ingresos/egresos MTD y margen libre. | `?mes=11&anio=2026` |
| **Flujo de Caja** | `GET` | `/api/v1/proyecciones/flujo-caja` | Serie temporal diaria a 30 días y días críticos de liquidez. | `?saldo_inicial=...&gasto_diario=...&umbral_reserva=...` |
| **Movimientos** | `GET` | `/api/v1/movimientos` | Histórico de transacciones contables del `Libro_Diario`. | `?limit=100&mes=11` |
| **Movimientos** | `POST`| `/api/v1/movimientos` | Registro atómico de ingreso o gasto (16 columnas tributarias). | `MovimientoCreate` (JSON) |
| **Movimientos (NLP)**| `POST`| `/api/v1/movimientos/parse` | Interpreta texto libre en lenguaje natural y extrae monto, tipo y comercio. | `{"texto": "Gasto 45.000 almuerzo en Don Vito"}` |
| **Obligaciones** | `GET` | `/api/v1/obligaciones` | Catálogo de pasivos financieros y deudas activas/pausadas. | Ninguno |
| **Obligaciones** | `POST`| `/api/v1/obligaciones` | Alta de nuevo crédito o pasivo a amortizar. | `ObligacionCreate` (JSON) |
| **Obligaciones** | `PUT` | `/api/v1/obligaciones/<id>` | Actualización de saldos, cuotas restantes o estado. | `ObligacionUpdate` (JSON) |
| **Obligaciones** | `DELETE`| `/api/v1/obligaciones/<id>`| Eliminación de una obligación. | Ninguno |
| **Obligaciones** | `POST`| `/api/v1/obligaciones/abonar` | Abono amortizado con asiento automático en `Libro_Diario`. | `{"id": "...", "monto": 500000}` |
| **Obligaciones** | `GET` | `/api/v1/obligaciones/vencimientos` | Calendario ordenado por día de vencimiento en el mes. | Ninguno |
| **Obligaciones** | `GET` | `/api/v1/obligaciones/foco` | Sugerencia de deuda prioritaria (estrategia avalancha/bola de nieve). | Ninguno |
| **Obligaciones** | `POST`| `/api/v1/obligaciones/proyectar-capacidad`| Simulación What-If (pausa de deudas e inyección de abonos). | `ProyeccionCapacidadRequest` (JSON) |
| **Dispositivos Push** | `POST`| `/api/v1/dispositivos/registrar` | Alta o actualización idempotente del token FCM de la app móvil. | `{"device_token": "...", "platform": "android"}` |
| **Dispositivos Push** | `GET` | `/api/v1/dispositivos` | Listado y conteo de dispositivos registrados activos. | Ninguno |
| **Dispositivos Push** | `POST`| `/api/v1/dispositivos/notificar` | Despacho de notificación push de prueba o broadcast. | `{"mensaje": "...", "titulo": "..."}` |
| **Asistencia** | `POST`| `/api/v1/asistencia/marcar` | Marcación de jornada laboral (Entrada, Pausa, Salida). | `{"accion": "entrada"}` |
| **Asistencia** | `POST`| `/api/v1/asistencia/materia` | Marcación de horas pedagógicas por cátedra. | `{"materia": "Física", "horas": 2}` |
| **Asistencia** | `GET` | `/api/v1/asistencia/materias` | Lista de materias académicas habilitadas. | Ninguno |
| **Asistencia** | `GET` | `/api/v1/asistencia/cierres` | Períodos laborales archivados. | Ninguno |
| **Cierres** | `GET` | `/api/v1/cierres` | Historial de cierres mensuales contables y laborales. | Ninguno |
| **Cierres** | `POST`| `/api/v1/cierres/ejecutar` | Ejecuta cierre mensual y genera comprobante PDF oficial. | `{"tipo": "contable", "hoja": "Octubre 2026"}` |
| **Cierres** | `GET` | `/api/v1/cierres/reportes/<file>` | Descarga binaria del comprobante PDF generado. | Ninguno |
| **Clima** | `GET` | `/api/v1/clima` | Pronóstico para Asunción con alerta preventiva de paraguas. | Ninguno |
| **Avisos & Agenda**| `GET` | `/api/v1/avisos` | Eventos y recordatorios sincronizados con Google Calendar. | Ninguno |
| **Avisos & Agenda**| `POST`| `/api/v1/avisos` | Creación de nuevo aviso con IA / Google Calendar. | `AvisoCreate` (JSON) |
| **Avisos & Agenda**| `DELETE`| `/api/v1/avisos/<id>` | Cancelación y desprogramación de recordatorio. | Ninguno |
| **Sincronización**| `POST`| `/api/v1/sincronizar` | Sincroniza datos entre SQLite local y Google Sheets. | `{"direccion": "local_to_sheets", "modulo": "laboral"}` |
| **Soporte** | `POST`| `/api/v1/soporte/tickets` | Creación de tickets de soporte técnico e incidencias. | `{"asunto": "...", "descripcion": "..."}` |
| **Webhooks (WhatsApp)**| `POST`| `/api/v1/webhooks/whatsapp` | Webhook asíncrono entrante de WhatsApp (`X-Webhook-Secret`). | Payload Evolution API |

---

## 🛠️ Guía de Integración para Gamma Mobile (Android v2)

### 1. DTOs Clave en Kotlin (Jetpack Compose)

#### Flujo de Caja a 30 Días (`GET /api/v1/proyecciones/flujo-caja`)
```kotlin
data class FlujoCajaResponse(
    @SerializedName("saldo_actual") val saldoActual: Double,
    @SerializedName("saldo_proyectado_30d") val saldoProyectado30d: Double,
    @SerializedName("total_ingresos_proyectados") val totalIngresosProyectados: Double,
    @SerializedName("total_gastos_fijos") val totalGastosFijos: Double,
    @SerializedName("total_gastos_variables_estimados") val totalGastosVariablesEstimados: Double,
    @SerializedName("dias_criticos") val diasCriticos: List<DiaCriticoDto>,
    @SerializedName("dias") val dias: List<FlujoCajaItemDiarioDto>
)

data class FlujoCajaItemDiarioDto(
    val fecha: String,
    @SerializedName("saldo_inicial") val saldoInicial: Double,
    val ingresos: Double,
    @SerializedName("egresos_fijos") val egresosFijos: Double,
    @SerializedName("egresos_variables") val egresosVariables: Double,
    @SerializedName("saldo_final") val saldoFinal: Double,
    val compromisos: List<String>
)
```

#### Parser Conversacional de Gastos (`POST /api/v1/movimientos/parse`)
```kotlin
data class ParseMovementRequest(val texto: String)

data class ParsedMovementDto(
    val valido: Boolean,
    val monto: Double,
    val moneda: String,
    @SerializedName("tipo_movimiento") val tipoMovimiento: String,
    val categoria: String,
    @SerializedName("proveedor_cliente") val proveedorCliente: String,
    val descripcion: String,
    val confianza: Double
)
```

#### Registro de Token Push (`POST /api/v1/dispositivos/registrar`)
```kotlin
data class DispositivoCreateDto(
    @SerializedName("device_token") val deviceToken: String,
    val platform: String = "android",
    @SerializedName("alias_usuario") val aliasUsuario: String = "Kevin"
)
```

### 2. Manejo de Errores y Resiliencia en la App

* **`HTTP 429 Too Many Requests`:** El backend incluye cabeceras `Retry-After: <segundos>`. La app debe aplicar un retroceso exponencial antes de reintentar.
* **`HTTP 413 Payload Too Large`:** La carga útil enviada supera el límite máximo de seguridad (64 KB).
* **`HTTP 422 Unprocessable Entity`:** Parámetros o DTOs con tipos o rangos inválidos; el cuerpo JSON describe los campos observados con el formato canónico de Pydantic v2.
* **`HTTP 401 Unauthorized`:** Clave `X-API-KEY` faltante o inválida.

---

## 📂 Estructura del Repositorio

```text
Gamma_bot/
├── src/                                # Código fuente modular
│   ├── adapters/                       # Adaptadores de infraestructura
│   │   └── notifications/              # Telegram, WhatsApp, Push y Mock adapters
│   ├── api/                            # Capa API REST v1
│   │   ├── v1/                         # Endpoints desacoplados por módulo
│   │   │   ├── routes_proyecciones.py  # Motor de flujo de caja 30d
│   │   │   ├── routes_dispositivos.py  # Registro y despacho push
│   │   │   ├── routes_webhooks.py      # Webhook WhatsApp asíncrono
│   │   │   ├── routes_movimientos.py   # Libro Diario y NLP Parser
│   │   │   └── ...                     # Dashboard, Asistencia, Obligaciones, etc.
│   │   ├── schemas.py                  # DTOs y validadores Pydantic v2
│   │   └── security.py                 # Rate limiter y auth por API Key
│   ├── app_queue/                      # Cola SQLite (cola.db) y worker concurrente
│   ├── com/                            # Bot interactivo de Telegram
│   ├── logic/                          # Lógica contable, amortizaciones y asistencia
│   ├── ports/                          # Puertos de abstracción (INotificationPort)
│   ├── repositories/                   # Persistencia dual (LocalRepository y SheetsRepository)
│   └── services/                       # Cashflow, Presupuesto, Clima, Calendar, Sync
├── docs/                               # Especificaciones SDD y contratos
│   ├── history/                        # Historiales archivados de fases v2.0.0
│   └── specs/                          # Artefactos SDD por módulo
├── data/                               # Bases de datos locales (gamma_local.db, dispositivos)
├── tests/                              # Suite de 480 pruebas unitarias y de integración
├── reportes/                           # Comprobantes y balances PDF generados
├── CHANGELOG.md                        # Registro histórico de versiones
├── HANDOFF.md                          # Estado actual del proyecto
├── pytest.ini                          # Configuración de pruebas
└── VERSION                             # 2.1.0
```

---

## 🧪 Verificación y Suite de Calidad

El proyecto mantiene una suite exhaustiva con **480 pruebas automáticas**:

```bash
# Ejecutar todas las pruebas unitarias y de integración
uv run pytest

# Verificación de formato de código (Black)
uv run black --check src/ tests/

# Análisis estático y linter (Flake8)
uv run flake8 src/ tests/

# Comprobación estricta de tipos (Mypy)
uv run mypy src/
```

---

## 🚀 Despliegue en Servidor (PythonAnywhere)

> [!IMPORTANT]
> **POLÍTICA DE DESPLIEGUE CONTROLADO:**
> Los cambios en producción se realizan exclusivamente sobre la rama `Main-stable` tras verificar que la suite de pruebas locales apruebe al 100%.

1. **Sincronización:**
   ```bash
   git fetch origin
   git checkout Main-stable
   git pull origin Main-stable
   ```
2. **Dependencias:**
   ```bash
   pip install --user -r requirements.txt
   ```
3. **Recarga de Aplicación Web:**
   Recargar la app desde la pestaña **Web** del panel de control de PythonAnywhere o tocando el archivo WSGI:
   ```bash
   touch /var/www/kevin11000_pythonanywhere_com_wsgi.py
   ```
