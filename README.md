# 🤖 GAMMA — Bot de Gestión Avanzada & Backend API

[![Version](https://img.shields.io/badge/version-1.18.2-blue.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-219%20passing-brightgreen.svg)](tests/)
[![Architecture](https://img.shields.io/badge/architecture-modular%20src-orange.svg)](src/)

**GAMMA** es un ecosistema integral y automatizado compuesto por un **Bot de Telegram** interactivo y un **Backend REST API** de alto rendimiento, diseñado para el control de asistencia laboral, gestión financiera estratégica, amortización de pasivos y agendamiento inteligente con IA.

Está optimizado para operar 24/7 en servidores cloud como **PythonAnywhere** e integrarse de manera nativa con **Google Sheets**, **Google Calendar**, **Google Gemini 2.5** y el cliente móvil **GammaMobile** (Android).

---

## 🚀 Características Principales

### 💰 Motor Financiero & Proyector de Capacidad (v1.18.0)
* **Proyector de Capacidad de Pago:** Evaluación cuantitativa de liquidez y endeudamiento mensual calculando margen neto, semáforo de viabilidad (`SUPERAVIT`, `AJUSTADO`, `DEFICIT`) y ratio DTI (*Debt-To-Income*).
* **Simulación What-If:** Estimación inmediata de meses de desendeudamiento ahorrados mediante inyección de abonos extraordinarios y alivio de liquidez pausando deudas específicas.
* **Timeline de Vencimientos:** Visualización cronológica ordenada de cuotas del mes con identificación de entidad financiera y alerta automática de cuotas vencidas.
* **Amortización Contable Real:** Registro atómico de abonos (`/abonar`), amortización de saldos/cuotas restantes y generación automática del asiento de egreso en `Libro_Diario` (`Categoría = "Préstamos / Deudas"`).
* **Pausado Flexible de Deudas:** Soporte de estados `Pausado` / `Pausada` para congelar temporalmente obligaciones sin alterar el historial contable.

### ⏱️ Control de Asistencia & Cierres Laborales
* **Marcación Inteligente:** Registro rápido de entradas, pausas, reanudaciones y salidas, con validación de rangos de jornada y detección automática de materias pedagógicas.
* **Historial Consolidado de Cierres:** Endpoint unificado de cierres contables (`Cierres_Historicos`) y cierres laborales con generación y descarga segura de comprobantes PDF generados con ReportLab.
* **Zona Horaria Oficial:** Alineación estricta con la hora paraguaya UTC-3 permanente (Ley Nº 7354/2024) mediante `datetime.timezone(timedelta(hours=-3))`.

### ⚡ Rendimiento, Caché y Resiliencia
* **`InMemorySheetsCache`:** Capa de almacenamiento en memoria con TTL configurable (180s para balances, movimientos y obligaciones; 300s para presupuestos) e invalidación atómica ante mutaciones, minimizando consumo de cuotas de Google Sheets API.
* **Manejo Estructurado de Rate Limiting:** Intercepción de `HTTP 429` (`RESOURCE_EXHAUSTED`) con respuestas amigables para clientes móviles.

### 🧠 Inteligencia Artificial & Avisos
* **Interpretación con Lenguaje Natural:** Extracción semántica de eventos y recordatorios mediante `gemini-2.5-flash`.
* **Sincronización con Google Calendar:** Agendamiento directo y bidireccional con control de alertas anti-spam escalonadas.

---

## 📱 Contratos REST API Móvil (`/api/v1`)

La API modular montada en Flask (`src/api/blueprint.py`) provee endpoints protegidos por API Key (`X-API-Key` o `Authorization: Bearer <key>`):

| Módulo | Método | Endpoint | Descripción |
|---|---|---|---|
| **Sistema** | `GET` | `/api/v1/health` | Estado del servicio, versión de API y enlace de descarga de APK. |
| **Sistema** | `GET` | `/api/v1/sistema/logs` | Consulta paginada e inversa de logs de ejecución. |
| **Dashboard** | `GET` | `/api/v1/dashboard/summary` | Resumen de saldos, ingresos/egresos del mes y margen libre. |
| **Asistencia**| `POST`| `/api/v1/asistencia/marcar` | Marcado de jornada laboral (entrada, salida, pausa). |
| **Asistencia**| `POST`| `/api/v1/asistencia/materia`| Marcado de horas por materia/cátedra específica. |
| **Movimientos**| `GET` | `/api/v1/movimientos` | Listado histórico de ingresos y egresos contables. |
| **Movimientos**| `POST`| `/api/v1/movimientos` | Registro de movimientos con desglose tributario (16 columnas). |
| **Cierres** | `GET` | `/api/v1/cierres` | Historial de cierres contables y laborales con metadatos PDF. |
| **Cierres** | `GET` | `/api/v1/cierres/reportes/<file>`| Descarga binaria de comprobantes PDF de cierre. |
| **Deudas** | `GET` | `/api/v1/obligaciones` | Consulta de obligaciones maestras (activas, pausadas, saldadas). |
| **Deudas** | `POST`| `/api/v1/obligaciones` | Alta de nueva deuda o compromiso financiero. |
| **Deudas** | `PUT` | `/api/v1/obligaciones/<id>` | Actualización de estado, saldos o cuotas. |
| **Deudas** | `DELETE`| `/api/v1/obligaciones/<id>`| Eliminación física de una obligación en la hoja maestra. |
| **Deudas** | `POST`| `/api/v1/obligaciones/abonar` | Abono amortizado con asiento contable en `Libro_Diario`. |
| **Deudas** | `GET` | `/api/v1/obligaciones/vencimientos` | Cronograma mensual ordenado por día de vencimiento. |
| **Deudas** | `GET` | `/api/v1/obligaciones/foco` | Recomendación de deuda prioritaria (estrategia avalancha/bola de nieve). |
| **Deudas** | `POST`| `/api/v1/obligaciones/proyectar-capacidad` | Motor de cálculo de capacidad de pago y simulador What-If. |
| **Avisos** | `GET` | `/api/v1/avisos` | Listado de avisos y eventos próximos sincronizados con Calendar. |
| **Avisos** | `POST`| `/api/v1/avisos` | Creación de recordatorio con agendamiento en Google Calendar. |
| **Avisos** | `PUT` | `/api/v1/avisos/<id>` | Modificación de evento agendado. |
| **Avisos** | `DELETE`| `/api/v1/avisos/<id>`| Cancelación y borrado de aviso. |

---

## 📂 Estructura del Repositorio

```text
Gamma_bot/
├── src/                        # Código fuente modular
│   ├── api/                    # API REST Flask (/api/v1) y esquemas Pydantic v2
│   │   ├── blueprint.py        # Definición de rutas y controladores REST
│   │   └── schemas.py          # DTOs y validadores de datos
│   ├── com/                    # Capa de presentación para Telegram Bot
│   │   ├── handlers/           # Manejadores de comandos (/start, /asistencia, etc.)
│   │   └── bot.py              # Inicialización y configuración de TeleBot
│   ├── logic/                  # Lógica de negocio y motores financieros
│   │   ├── financiero.py       # Motor contable, amortizaciones y proyector de capacidad
│   │   ├── logic.py            # Agente autónomo de asistencia y cron jobs
│   │   ├── constants.py        # Esquemas de hojas, columnas y constantes de negocio
│   │   └── vigia.py            # Auditoría y resolución de inconsistencias
│   ├── repositories/           # Capa de persistencia
│   │   └── sheets_repository.py# Cliente Google Sheets con InMemorySheetsCache
│   └── services/               # Integraciones externas (Calendar, Telegram, etc.)
├── docs/                       # Especificaciones SDD, historia de fases y contratos
│   ├── history/                # Handoffs archivados de fases anteriores
│   └── specs/                  # Especificaciones activas por funcionalidad
├── tests/                      # Suite de pruebas unitarias y de integración
├── reportes/                   # Directorio de almacenamiento de comprobantes PDF
├── CHANGELOG.md                # Registro cronológico de cambios por versión
├── HANDOFF.md                  # Estado actual de transición y pendientes
├── requirements.txt            # Dependencias del proyecto
└── VERSION                     # Número semántico de versión actual
```

---

## 🛠️ Stack Tecnológico

* **Lenguaje:** Python 3.13+
* **Backend Web:** Flask, Flask-Limiter, Pydantic v2
* **Telegram Bot:** `pyTelegramBotAPI` (TeleBot)
* **Integración Cloud:** `gspread`, `google-auth`, `google-api-python-client`
* **Inteligencia Artificial:** `google-genai` (Gemini 2.5)
* **Diseño Documental:** `reportlab` (Generación de PDFs contables)
* **Testing & Calidad:** `pytest`, `pytest-cov`, `flake8`, `black`

---

## 🧪 Pruebas y Validación Local

El proyecto cuenta con una cobertura integral de pruebas unitarias y de integración:

```bash
# Ejecutar la suite completa de pruebas
uv run pytest

# Verificar cumplimiento de estilo y sintaxis
uv run flake8 src/api/blueprint.py src/api/schemas.py src/logic/constants.py src/logic/financiero.py src/logic/logic.py src/repositories/sheets_repository.py tests/

# Comprobar formato con Black
uv run black --check src/ tests/
```

---

## 🚀 Despliegue en PythonAnywhere

1. **Sincronización:** Hacer pull de la rama `Main-stable` en el servidor:
   ```bash
   git fetch origin
   git checkout Main-stable
   git pull origin Main-stable
   ```
2. **Entorno Virtual & Dependencias:**
   ```bash
   pip install --user -r requirements.txt
   ```
3. **Recarga de Web App:** Recargar la aplicación web desde el panel de control de PythonAnywhere o tocando el archivo WSGI configurado.
