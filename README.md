# 🤖 GAMMA — Bot de Gestión Avanzada (Marcaciones, Reportes e IA)

**GAMMA** es un ecosistema automatizado en forma de bot de Telegram diseñado para optimizar el registro de horas laborales, la gestión financiera y el agendamiento inteligente de recordatorios. Construido sobre la API de Telegram y completamente integrado con **Google Sheets** y **Gemini 2.5**, está optimizado para funcionar las 24 horas del día en entornos de servidor como **PythonAnywhere**.

---

## 🚀 Características Principales

*   **⏱️ Sistema Inteligente de Marcado:** Control de asistencia dinámico en Google Sheets mediante comandos interactivos. Soporta jornadas normales con pausas de almuerzo o salidas directas.
*   **🧠 Agendamiento con Lenguaje Natural:** Interpretación semántica de mensajes libres (ej: *"hacer el laboratorio mañana a la tarde"*) utilizando el modelo `gemini-2.5-flash` para extraer hitos con precisión cronológica.
*   **📋 Panel Visual de Avisos:** Interfaz móvil interactiva con cuadrículas de botones en tiempo real para visualizar, limpiar de forma automática y eliminar recordatorios en caliente sin generar spam en el chat.
*   **🔔 Control de Alertas Anti-Spam:** Sistema de notificaciones programadas por hitos temporales que avisa de manera automática a los 30, 7, 5, 3 y 1 días de anticipación de cada evento.
*   **📊 Generación de Reportes Financieros en PDF:** Al cerrar un ciclo, calcula automáticamente las horas acumuladas basándose en fórmulas dinámicas de Sheets, aplica descuentos personalizados si se solicita y genera un reporte contable PDF estilizado con ReportLab.

---

## 🛠️ Stack Tecnológico

*   **Lenguaje:** Python 3.x
*   **Framework de Bot:** `pyTelegramBotAPI` (TeleBot)
*   **Integración Cloud:** `gspread` & `google-oauth2` (Google Sheets API)
*   **Motor de IA:** `google-genai` (Gemini 2.5 API)
*   **Diseño de Documentos:** `reportlab` (Generación de PDF)
*   **Manejo del Tiempo:** `pytz` (Anclado estricto a la zona horaria de Paraguay/Bs.As.)

---

## 📂 Estructura del Proyecto

```text
mysite/
│
├── bot.py                  # Orquestador del Bot, manejadores de comandos y botones
├── logic/
│   └── logic.py            # Núcleo lógico: Sheets, PDF, Gemini e hilos de control
├── reportes/               # Repositorio local de PDFs contables generados
├── .env                    # Variables de entorno confidenciales
├── credentials.json        # Claves de acceso de Google Cloud Service Account
├── periodo_actual.txt      # Pestaña activa del mes en Google Sheets
└── avisos.json             # Base de datos persistente para alertas temporales
