# Especificación Técnica de Proyecto: Migración de Gamma Bot a Android (Gamma Mobile)

## 1\. Metadatos del Proyecto y Entorno Operativo

- **Nombre del Proyecto:** Gamma Mobile (Android)  
- **Repositorio Base:** `KEVIN11000/Gamma_bot`  
- **Rama Base:** `Main-stable`  
- **Ruta de Despliegue Backend:** PythonAnywhere (`/home/kevin11000/mysite`)  
- **Runtime Backend:** Python 3.10+ / FastAPI / Uvicorn  
- **Base de Datos Operacional (Nube):** Google Sheets (Spreadsheet: `Libros contables`) con autenticación Service Account (`credentials.json`).  
- **Estructura de Hojas Maestras:**  
  - `Libro_Diario`: Ledger transaccional continuo y no destructivo.  
  - `Obligaciones_Maestro`: Registro de proyectos y deudas en amortización.  
  - `Cierres_Historicos`: Consolidación mensual (1 fila por mes, IVA y saldo acumulado).  
  - `Presupuesto_Base`: Ingresos fijos y gastos obligatorios de referencia.  
  - `Soporte_Tickets`: Registro de incidencias y feedback de usuario (`TCK-xxx`).  
- **Base de Datos Operacional (Local Backend):**  
  - `avisos.json`: Persistencia plana de eventos y recordatorios con hitos temporales.  
- **Motor de Inteligencia Artificial:** Google GenAI API (`gemini-2.5-flash`) mediante SDK `google-genai`.  
- **Stack Móvil Objetivo:** Android Nativo (Kotlin \+ Jetpack Compose \+ Material 3\) o Flutter (Dart).  
- **Zona Horaria Oficial:** `America/Asuncion` (UTC-3).  
- **Régimen Fiscal:** Paraguay (IVA 10%, IVA 5%, Exento, Crédito Fiscal y Débito Fiscal).

---

## 2\. Diagnóstico del Sistema Actual y Enfoque de Desacoplamiento

### 2.1 Estado del Código en `KEVIN11000/Gamma_bot`

1. **`bot.py` (Capa de Presentación Telegram):**  
   - Utiliza `telebot` (`pyTelegramBotAPI`) en modo polling.  
   - Maneja enrutamiento de comandos (`/start`, `/marcar`, `/cierre`, `/aviso`, `/avisos`, `/abonar`, `/simular`).  
   - Mantiene estados conversacionales en memoria (`self.avisos_pendientes`).  
   - Vincula directamente la interacción del usuario con `logic/logic.py`.  
2. **`logic/logic.py` (Capa de Dominio y Datos):**  
   - Instancia la clase `AgenteAutonomoHoras`.  
   - Conexión con Google Sheets mediante `gspread`.  
   - Lógica fiscal paraguaya: discriminación automática de base gravada, monto de IVA (10% o 5%) y clasificación en Débito/Crédito Fiscal.  
   - Lógica de pasivos: amortización contra `Obligaciones_Maestro`, actualización de `Saldo_Actual` y cierre automático a `Saldado`.  
   - Método `interpretar_frase_con_ia()`: Utiliza Gemini 2.5 Flash con salida JSON estructurada para extraer título, fecha y hora.  
   - Generación de reportes financieros en PDF con `reportlab`.  
3. **`avisos.json` (Motor de Alertas):**  
   - Array de objetos con estructura: `titulo`, `fecha_evento` ("DD/MM/AAAA HH:MM"), `alertas_disparadas` (hitos `["30", "7", "5", "3", "1"]`).

### 2.2 Estrategia de Migración: Backend for Frontend (BFF)

Migrar la lógica completa al cliente Android requeriría embeber `credentials.json` de Google Cloud y la clave `GEMINI_API_KEY` en el APK, exponiendo credenciales críticas, además de duplicar el código contable en Kotlin/Dart.

La arquitectura desacoplada establece:

1. **Backend Gateway (FastAPI en `mysite/`):**  
   - Se crea `mysite/api/` exponiendo una API REST ligera.  
   - Reutiliza directamente las funciones operativas de `logic/logic.py`.  
   - Protege los secretos del servidor y centraliza el acceso concurrente a Google Sheets.  
   - Permite que el bot de Telegram y la app de Android coexistan operando sobre los mismos libros contables.  
2. **Cliente Android (Gamma Mobile):**  
   - Consume la API REST mediante HTTPS con autenticación por Bearer Token / `X-API-KEY`.  
   - Implementa almacenamiento local (Room Database) para funcionamiento offline-first.  
   - Gestiona notificaciones locales de recordatorios con `WorkManager` sin depender de servicios push externos complejos.

---

## 3\. Arquitectura del Sistema

┌────────────────────────────────────────────────────────┐

│                   Cliente Android                      │

│        (Kotlin \+ Jetpack Compose / Flutter)            │

│  \- Presentation Layer: UI Material 3 \+ StateFlow       │

│  \- Domain Layer: UseCases de Negocio Móvil             │

│  \- Data Layer: Room DB (Cache) \+ Retrofit (API Client) │

│  \- Background: WorkManager (Alarmas locales de Avisos) │

└───────────────────────────┬────────────────────────────┘

                            │ HTTPS (JSON \+ Bearer/API-Key)

┌───────────────────────────▼────────────────────────────┐

│      Backend API Gateway (PythonAnywhere / mysite)     │

│                 FastAPI (api/main.py)                  │

│  \- Router /api/v1 (auth, movimientos, obligaciones)    │

│  \- Middlewares: CORS, Rate Limiting, API Key Auth      │

│  \- Pydantic Models (Validación estricta de tipos)      │

└─────────────┬────────────────────────────┬─────────────┘

              │ Reutilización directa      │

┌─────────────▼──────────────┐   ┌─────────▼─────────────┐

│       logic/logic.py       │   │    Google GenAI SDK   │

│  \- AgenteAutonomoHoras     │   │  \- Gemini 2.5 Flash   │

│  \- Cálculos contables      │   │  \- JSON Extraction    │

│  \- IVA paraguayo (10/5%)   │   └───────────────────────┘

│  \- gspread (Service Acct)  │

└─────────────┬──────────────┘

              │ Lectura / Escritura

┌─────────────▼──────────────────────────────────────────┐

│      Google Sheets (Libros contables \- 4 Pestañas)     │

│  \- Libro\_Diario (Transacciones continuas)              │

│  \- Obligaciones\_Maestro (Deudas y proyectos activos)   │

│  \- Cierres\_Historicos (1 fila resumen por mes)         │

│  \- Presupuesto\_Base (Flujos y márgenes de seguridad)   │

└────────────────────────────────────────────────────────┘

---

## 4\. Contrato de API REST (FastAPI)

### 4.1 Modelos de Datos Pydantic (`api/schemas.py`)

from pydantic import BaseModel, Field

from typing import Optional, List

from enum import Enum

class TipoMovimiento(str, Enum):

    INGRESO \= "Ingreso"

    GASTO \= "Gasto"

class TasaIVA(str, Enum):

    IVA\_10 \= "10%"

    IVA\_5 \= "5%"

    EXENTO \= "Exento"

class TipoComprobante(str, Enum):

    VIRTUAL\_LEGAL \= "Virtual Legal"

    FISICA\_LEGAL \= "Física Legal"

    NO\_LEGAL \= "No Legal"

class MovimientoCreate(BaseModel):

    fecha: str \= Field(..., description="Formato DD/MM")

    movimiento: TipoMovimiento

    proveedor\_cliente: str

    nro\_factura: Optional\[str\] \= "S/N"

    total: int \= Field(..., gt=0, description="Monto total en Guaraníes (₲)")

    categoria: str

    comprobante: TipoComprobante \= TipoComprobante.NO\_LEGAL

    tasa\_iva: TasaIVA \= TasaIVA.IVA\_10

    id\_obligacion: Optional\[str\] \= None

    rastro\_foto: Optional\[str\] \= ""

class MovimientoResponse(MovimientoCreate):

    neto: int

    iva: int

    monto\_gravado: int

    monto\_iva: int

    clasificacion\_iva: str

    mes: str

class ObligacionCreate(BaseModel):

    tipo: str \= Field(..., regex="^(Deuda|Proyecto)\$")

    nombre: str

    monto\_inicial: int \= Field(..., gt=0)

    cuota\_referencia\_gs: Optional\[int\] \= 0

    observaciones: Optional\[str\] \= ""

class ObligacionResponse(ObligacionCreate):

    id\_obligacion: str

    saldo\_actual: int

    estado: str  \# Simulado, Activo, Saldado

    fecha\_inicio: str

class AbonoRequest(BaseModel):

    id\_obligacion: str

    monto: int \= Field(..., gt=0)

    nro\_factura: Optional\[str\] \= "S/N"

    tasa\_iva: TasaIVA \= TasaIVA.IVA\_10

class SimulacionRequest(BaseModel):

    monto: int \= Field(..., gt=0)

    meses: int \= Field(..., gt=0)

    concepto: Optional\[str\] \= "Simulación General"

class SimulacionResponse(BaseModel):

    cuota\_mensual: int

    margen\_actual: int

    nuevo\_margen: int

    diagnostico: str  \# Viable, Ajustado, Riesgo

    detalles: str

class AvisoItem(BaseModel):

    indice: Optional\[int\] \= None

    titulo: str

    fecha\_evento: str  \# DD/MM/AAAA HH:MM

    dias\_restantes: Optional\[int\] \= None

    alertas\_disparadas: List\[str\] \= \[\]

class IAParseRequest(BaseModel):

    frase: str

class IAParseResponse(BaseModel):

    titulo: Optional\[str\]

    fecha: Optional\[str\]  \# DD/MM/AAAA

    hora: Optional\[str\]   \# HH:MM

    monto: Optional\[int\] \= None

    categoria: Optional\[str\] \= None

    tasa\_iva: Optional\[str\] \= None

### 4.2 Catálogo de Endpoints REST (`api/routers/`)

| Método | Endpoint | Descripción | Parámetros / Body |
| :---- | :---- | :---- | :---- |
| `POST` | `/api/v1/auth/verify` | Valida el API Key del cliente móvil | Headers: `X-API-KEY` |
| `GET` | `/api/v1/dashboard/summary` | Balance financiero mensual consolidado | Query: `mes` (opcional) |
| `GET` | `/api/v1/movimientos` | Listado de transacciones de `Libro_Diario` | Query: `mes`, `categoria`, `limit` |
| `POST` | `/api/v1/movimientos` | Registra ingreso o gasto con cálculo de IVA | Body: `MovimientoCreate` |
| `GET` | `/api/v1/obligaciones` | Lista de deudas y proyectos | Query: `estado` (Activo, Simulado) |
| `POST` | `/api/v1/obligaciones` | Da de alta una nueva deuda o proyecto | Body: `ObligacionCreate` |
| `POST` | `/api/v1/obligaciones/simular` | Evalúa viabilidad contra el margen libre | Body: `SimulacionRequest` |
| `POST` | `/api/v1/obligaciones/aprobar/{id}` | Pasa un proyecto de Simulado a Activo | Path: `id` |
| `POST` | `/api/v1/obligaciones/abonar` | Amortiza deuda e inserta gasto en Diario | Body: `AbonoRequest` |
| `GET` | `/api/v1/avisos` | Lista de recordatorios en `avisos.json` | Ninguno |
| `POST` | `/api/v1/avisos` | Crea recordatorio (vía texto o NLP) | Body: `AvisoItem` |
| `DELETE` | `/api/v1/avisos/{indice}` | Elimina recordatorio por índice | Path: `indice` |
| `POST` | `/api/v1/ia/interpretar` | Procesa frase con Gemini 2.5 Flash | Body: `IAParseRequest` |
| `POST` | `/api/v1/cierres/ejecutar` | Genera balance mensual y PDF en Drive | Body: `{"mes": "Octubre", "anio": 2026}` |

---

## 5\. Diseño del Cliente Móvil Android (Gamma Mobile)

### 5.1 Estructura del Proyecto Android (Clean Architecture)

app/src/main/java/com/kevin/gammamobile/

├── data/

│   ├── local/

│   │   ├── GammaDatabase.kt          \# Room Database

│   │   ├── dao/                      \# MovimientoDao, ObligacionDao, AvisoDao

│   │   └── entity/                   \# Entidades locales con timestamp de sync

│   ├── remote/

│   │   ├── GammaApiService.kt        \# Interfaz Retrofit

│   │   └── dto/                      \# Data Transfer Objects

│   └── repository/

│       └── GammaRepositoryImpl.kt    \# Estrategia de cache y fallback de red

├── domain/

│   ├── model/                        \# Modelos puros de dominio

│   └── usecase/                      \# GetDashboardSummary, RegistrarMovimiento, etc.

├── presentation/

│   ├── navigation/                   \# NavHost y Rutas Compose

│   ├── dashboard/                    \# DashboardScreen & DashboardViewModel

│   ├── transacciones/                \# TransaccionesScreen & FormularioTransaccionScreen

│   ├── obligaciones/                 \# ObligacionesScreen & SimuladorModal

│   ├── avisos/                       \# AvisosScreen & DetalleAvisoDialog

│   └── theme/                        \# Material 3 ColorScheme (Dark/Light)

└── worker/

    ├── SyncMovimientosWorker.kt      \# Encolamiento offline de transacciones

    └── AlarmaAvisosWorker.kt         \# Disparador diario de notificaciones locales

### 5.2 Módulos y Pantallas de la Interfaz de Usuario (UI)

1. **Dashboard Principal (`DashboardScreen`):**  
     
   - **Tarjeta de Posición Financiera:** Margen Libre Disponible (₲), Saldo Acumulado y Posición de IVA (Débito vs. Crédito Fiscal).  
   - **Banner de Alertas Inminentes:** Carrusel horizontal de recordatorios con vencimiento menor a 5 días.  
   - **Botón Flotante de Acción (FAB):** Acceso inmediato a "Nueva Transacción" y "Nuevo Recordatorio".

   

2. **Libro Diario (`TransaccionesScreen`):**  
     
   - Lista infinita reactiva agrupada por fecha.  
   - Filtros rápidos por botones segmentados (Chips): Todos, Gastos, Ingresos, Deudas.  
   - Badge visual según tipo de comprobante (Legal 10%, Legal 5%, No Legal).

   

3. **Carga Inteligente de Transacción (`NuevaTransaccionScreen`):**  
     
   - **Pestaña 1: Carga Asistida por IA (Gemini 2.5 Flash):**  
     - Campo de texto libre con micrófono para dictado ("Compré repuestos por 250000 con factura crédito fiscal").  
     - Botón "Interpretar con IA": Envía el texto a `/api/v1/ia/interpretar` y precarga los campos estructurados en 1 segundo.  
   - **Pestaña 2: Carga Manual:**  
     - Selectores numéricos directos con cálculo automático de IVA y campo opcional para asociar a una obligación activa.

   

4. **Gestión de Obligaciones y Deudas (`ObligacionesScreen`):**  
     
   - Indicador de progreso circular o barra lineal con porcentaje de amortización (`Saldo_Actual / Monto_Inicial`).  
   - Botón directo "Abonar" que abre modal precargado y descuenta automáticamente el saldo.  
   - Pestaña de "Simulador": Sliders para monto y meses que proyectan el impacto en el margen mensual en tiempo real.

---

## 6\. Persistencia Local, Modo Offline y Notificaciones

### 6.1 Sincronización Offline-First (Room \+ WorkManager)

- Todas las lecturas (`Dashboard`, `Transacciones`, `Obligaciones`) se sirven primero desde la base de datos Room local.  
- Al registrar un movimiento sin conexión a internet:  
  1. Se guarda en Room con estado `sync_status = "PENDING"`.  
  2. La UI actualiza inmediatamente el balance de forma optimista.  
  3. `SyncMovimientosWorker` se encola con restricciones de red (`NetworkType.CONNECTED`). Al restablecerse la conectividad, ejecuta `POST /api/v1/movimientos` y actualiza a `sync_status = "SYNCED"`.

### 6.2 Notificaciones Locales de Recordatorios (`AvisosWorker`)

- Para evitar costos de servidores push o sockets permanentes en PythonAnywhere:  
  - `AvisosWorker` se programa en el dispositivo Android mediante `WorkManager` con periodicidad diaria a las 08:00 AM (hora Paraguay).  
  - Consulta `avisos.json` en caché local.  
  - Si la diferencia de días coincide con los hitos oficiales (`30, 7, 5, 3, 1`), lanza una notificación local al sistema de notificaciones de Android con sonido y vibración.

---

## 7\. Backlog Técnico y Tickets de Ejecución para Agentes de Antigravity

### Módulo A: Backend API Gateway (PythonAnywhere / `mysite`)

#### `TICKET-MOB-01`: Inicialización del Gateway FastAPI y Seguridad

- **Archivos:** `mysite/api/__init__.py`, `mysite/api/main.py`, `mysite/api/security.py`, `mysite/.env`  
- **Tareas:**  
  1. Configurar aplicación FastAPI con middleware CORS (`allow_origins=["*"]`).  
  2. Implementar middleware de autenticación mediante encabezado `X-API-KEY` validado contra `.env`.  
  3. Endpoint de diagnóstico `GET /api/v1/health` que verifique conexión con Google Sheets y estado de `avisos.json`.  
- **Criterio de Aceptación:** Peticiones sin `X-API-KEY` retornan `HTTP 401 Unauthorized`. `GET /health` responde `HTTP 200` con status `ok`.

#### `TICKET-MOB-02`: Desacoplamiento de `logic/logic.py`

- **Archivos:** `mysite/logic/logic.py`  
- **Tareas:**  
  1. Extraer los métodos de cálculo contable y persistencia de `AgenteAutonomoHoras` para que retornen tipos de datos estándar de Python (`dict`, `list`) en lugar de strings con formato para Telegram.  
  2. Mantener retrocompatibilidad con `bot.py` para asegurar que el bot de Telegram siga operando sin regresiones.  
- **Criterio de Aceptación:** Pruebas unitarias de `logic.py` (`pytest -v`) pasan en verde sin errores de importación ni formato flake8.

#### `TICKET-MOB-03`: Endpoints Transaccionales de Libro Diario y Obligaciones

- **Archivos:** `mysite/api/routers/contabilidad.py`, `mysite/api/schemas.py`  
- **Tareas:**  
  1. Implementar `GET /api/v1/dashboard/summary`: consolidación del mes activo.  
  2. Implementar `GET /api/v1/movimientos` y `POST /api/v1/movimientos` con validación de tasas (10%, 5%, Exento).  
  3. Implementar `GET /api/v1/obligaciones`, `POST /api/v1/obligaciones/simular` y `POST /api/v1/obligaciones/abonar`.  
- **Criterio de Aceptación:** Inserción exitosa de filas en Google Sheets (`Libro_Diario` y `Obligaciones_Maestro`) con cálculo fiscal correcto.

#### `TICKET-MOB-04`: Endpoints de IA y Gestión de Avisos

- **Archivos:** `mysite/api/routers/asistente.py`  
- **Tareas:**  
  1. Endpoint `POST /api/v1/ia/interpretar`: expone Gemini 2.5 Flash (`google-genai`) para estructurar frases de gastos o eventos.  
  2. Endpoints CRUD para `avisos.json`: `GET /api/v1/avisos`, `POST /api/v1/avisos`, `DELETE /api/v1/avisos/{indice}`.  
- **Criterio de Aceptación:** Retorno de JSON estricto con zona horaria `America/Asuncion` y persistencia en `avisos.json`.

---

### Módulo B: Frontend Android (Gamma Mobile)

#### `TICKET-MOB-05`: Scaffolding del Proyecto Android y Capa de Red

- **Archivos:** `build.gradle.kts`, `app/build.gradle.kts`, `di/NetworkModule.kt`  
- **Tareas:**  
  1. Crear proyecto Android con soporte mínimo SDK 26 (Android 8.0) y target SDK 34/35.  
  2. Configurar Hilt para inyección de dependencias y Retrofit/OkHttp con Interceptor para `X-API-KEY`.  
  3. Configurar modelos DTO y manejo de respuestas selladas (`NetworkResult<T>`).  
- **Criterio de Aceptación:** Conexión exitosa contra el endpoint `/api/v1/health` y log en Logcat.

#### `TICKET-MOB-06`: Persistencia Local con Room (Offline-First)

- **Archivos:** `data/local/GammaDatabase.kt`, `data/local/entity/*`, `data/local/dao/*`  
- **Tareas:**  
  1. Crear entidades `MovimientoEntity`, `ObligacionEntity`, `AvisoEntity`.  
  2. Implementar DAOs con soporte para consultas Flow reactivas.  
  3. Implementar `GammaRepositoryImpl` con estrategia de lectura local y sincronización remota.  
- **Criterio de Aceptación:** La app muestra los datos persistidos en Room incluso en modo avión.

#### `TICKET-MOB-07`: Implementación de DashboardScreen y TransaccionesScreen

- **Archivos:** `presentation/dashboard/*`, `presentation/transacciones/*`  
- **Tareas:**  
  1. Diseñar tarjetas Material 3 con formato de moneda en Guaraníes (`#,##0 ₲`).  
  2. Implementar lista de transacciones con filtrado por tipo y categoría.  
  3. Componente Swipe-to-refresh para sincronización manual.  
- **Criterio de Aceptación:** Renderizado fluido a 60/120 fps y actualización reactiva al recibir nuevos datos.

#### `TICKET-MOB-08`: Formulario Inteligente de Transacciones (Manual \+ Gemini NLP)

- **Archivos:** `presentation/transacciones/NuevaTransaccionScreen.kt`  
- **Tareas:**  
  1. Formulario con inputs para monto, categoría, tipo y selector de IVA.  
  2. Caja de texto para dictado/escritura libre con botón "Procesar con IA".  
  3. Vinculación del retorno de `/api/v1/ia/interpretar` con los campos del formulario.  
- **Criterio de Aceptación:** Una frase como "Gasto 50.000 combustible factura 10" rellena automáticamente los campos correspondientes.

#### `TICKET-MOB-09`: Módulo de Obligaciones y Simulador de Proyectos

- **Archivos:** `presentation/obligaciones/*`  
- **Tareas:**  
  1. Listado de obligaciones con barra de progreso de saldo pendiente.  
  2. Modal de abono rápido que dispara `POST /api/v1/obligaciones/abonar`.  
  3. Pantalla de simulación con cálculo de viabilidad (indicadores Verde, Amarillo, Rojo).  
- **Criterio de Aceptación:** El simulador muestra advertencia de déficit si la cuota supera el margen disponible.

#### `TICKET-MOB-10`: Programación de Notificaciones y Sincronización con WorkManager

- **Archivos:** `worker/SyncMovimientosWorker.kt`, `worker/AlarmaAvisosWorker.kt`  
- **Tareas:**  
  1. Configurar `SyncMovimientosWorker` con reintento exponencial (`BackoffPolicy.EXPONENTIAL`).  
  2. Configurar `PeriodicWorkRequestBuilder` para `AlarmaAvisosWorker` cada 24 horas.  
  3. Crear canal de notificaciones Android (`NotificationChannel`) para recordatorios contables.  
- **Criterio de Aceptación:** Se dispara notificación en la barra de estado cuando faltan 5, 3 o 1 días para un evento registrado.

---

### Módulo C: Integración Continua (CI/CD)

#### `TICKET-MOB-11`: Pipeline de GitHub Actions

- **Archivos:** `.github/workflows/ci.yml`  
- **Tareas:**  
  1. Job de backend: ejecución de `flake8` y `pytest` para la API y `logic/logic.py`.  
  2. Job de Android: compilación de `./gradlew assembleDebug` y ejecución de pruebas unitarias locales.  
- **Criterio de Aceptación:** Workflow completo en verde ante cada push a la rama `Main-stable`.