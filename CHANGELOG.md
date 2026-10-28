# Changelog — Gamma Bot

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.18.1] - 2026-10-28

### Añadido
* **Generador de Planillas Nativas Excel (`ExcelReportService`):**
  * Generación de archivos `.xlsx` oficiales con grilla de marcaciones A-G y fórmulas dinámicas de suma, porcentaje de IVA y cuadro resumen de cobro mensual.
* **Motor de Analíticas Laborales MTD:**
  * Cálculo de horas perdidas (< 8h estándar en jornadas trabajadas), horas extras (> 8h) y balance neto acumulado.
  * Formateo legible de horas decimales (`Xh Ym`) y cómputo de salario devengado MTD.
* **Consulta Unificada de Períodos Activos:**
  * Función `obtener_estado_periodos` para verificar sincronización entre marcación laboral (`periodo_actual.txt`) y contabilidad (`Libro_Diario` / `Cierres_Historicos`).
* **Endpoints REST en `mobile_api`:**
  * `GET /api/v1/asistencia/periodos`: Consulta de sincronización de períodos.
  * `GET /api/v1/asistencia/analiticas`: Métricas MTD de asistencia y horas perdidas/extras.
  * `GET /api/v1/asistencia/reporte/excel`: Descarga binaria de planilla `.xlsx`.
  * `GET /api/v1/asistencia/reporte/pdf`: Descarga binaria de reporte `.pdf`.
* **Comandos de Telegram y Entrega Dual:**
  * Handlers para `/horas` y `/periodo` con tarjetas interactivas en Markdown.
  * Flujo de `/reporte` actualizado para adjuntar de forma automática ambos documentos (Excel y PDF).

### Modificado
* **Paridad Oficial de Cuadro Resumen:**
  * Normalización de dos columnas (`Resumen` / `Cantidades`) con conceptos: `mes`, `hora`, `por Horas`, `IVA 10%`, `INCLUIDO`, y fila opcional `SALDO ANTERIOR` / `Descuento` (solo si el monto es distinto de 0), finalizando en `FACTURA`.

## [1.18.0] - 2026-10-22

### Añadido
* **Proyector de Capacidad de Pago (`POST /api/v1/obligaciones/proyectar-capacidad`):**
  * Cálculo dinámico de compromiso mensual total, fondos de maniobra disponibles y capacidad neta de endeudamiento.
  * Semáforo de viabilidad financiera (`SUPERAVIT`, `AJUSTADO`, `DEFICIT`) con cálculo automático de ratio DTI (*Debt-To-Income*).
  * Simulación de escenarios *What-If*: estimación de meses ahorrados mediante abonos extraordinarios y cálculo de alivio de liquidez pausando deudas específicas.
* **Timeline Cronológico de Vencimientos (`GET /api/v1/obligaciones/vencimientos`):**
  * Retorno estructurado de obligaciones activas ordenadas por día de vencimiento mensual.
  * Inclusión de metadatos de entidad financiera y flag booleano `vencida` evaluado en base al día actual.
* **Deuda Foco y Amortización (`GET /api/v1/obligaciones/foco`):**
  * Endpoint con parámetro `?criterio=prioridad|saldo` para priorizar amortización por método bola de nieve o avalancha.
* **Historial Consolidado de Cierres (`GET /api/v1/cierres`):**
  * Consolidación de cierres contables (`Cierres_Historicos`) y cierres de asistencia laboral (`REPORTES_DIR`).
  * Endpoint de descarga segura de comprobantes PDF generados (`GET /api/v1/cierres/reportes/<filename>`).
* **Soporte de Columna `Entidad`:**
  * Columna D (índice 3) en la hoja `Obligaciones_Maestro`, persistencia garantizada en alta, simulación y serialización REST.
* **Caché en Memoria (`InMemorySheetsCache`):**
  * Implementación de capa de caché en memoria con TTL diferenciado (180s para balances, movimientos y obligaciones; 300s para presupuestos) e invalidación atómica en escrituras.

### Modificado
* **Amortización Contable Real (`POST /api/v1/obligaciones/abonar`):**
  * Amortización real de saldo y cuotas restantes; transición automática a estado `Saldada` al liquidar la totalidad.
  * Asiento contable de egreso automático en `Libro_Diario` bajo la categoría `"Préstamos / Deudas"` con tasa exenta.
* **Pausado de Obligaciones:**
  * Soporte formal de estados `"Pausado"` y `"Pausada"`.
  * Exclusión automática de deudas pausadas en los cálculos de margen de ataque, cola de deudas, cronograma de vencimientos y proyector de capacidad.
* **Zona Horaria y Detección de Período:**
  * Sincronización estricta con el huso horario oficial de Paraguay UTC-3 (`timezone(timedelta(hours=-3))`) en cumplimiento de la Ley Nº 7354/2024.
  * Detección dinámica de períodos en `AgenteAutonomoHoras`, eliminando referencias históricas fijas.

### Resiliencia y Correcciones
* **Mitigación de Rate Limiting (Google Sheets API):**
  * Captura de excepciones `HTTP 429 Too Many Requests` (`RESOURCE_EXHAUSTED`) en endpoints de asistencia (`/asistencia/marcar` y `/asistencia/materia`) con respuesta limpia para el cliente móvil.

---

## [1.17.0] - 2026-10-20

### Añadido
* **Integración y Contratos para GammaMobile v0.0.9:**
  * Control de asistencia móvil (`POST /api/v1/asistencia/marcar` y `/asistencia/materia`) con validación de rangos y estados HTTP estructurados.
  * Desglose tributario en `POST /api/v1/movimientos` (16 columnas contables e impuestos discriminados).
  * Auto-sincronización salarial hacia `Presupuesto_Base` (`upsert_salario_presupuesto_base`).
  * CRUD completo de avisos sincronizado con Google Calendar (`/api/v1/avisos`).
  * Endpoint de consulta de logs de sistema (`GET /api/v1/sistema/logs`) con lectura inversa y normalización ISO 8601.
  * Ciclo de vida y simulación de deudas (`POST /api/v1/obligaciones/simular`).

### Modificado
* Resolución unificada de `LIBRO_CONTABLE_ID` con fallback a `SPREADSHEET_ID`.
* Headers HTTP de invalidación de caché en respuestas dinámicas de dashboard y movimientos.

---

## [1.16.2] - 2026-10-13

### Añadido
* Gestión guiada de gastos fijos y presupuesto base.
* Integración de Webhook para sincronización reactiva de GitHub Issues.

### Corregido
* Resolución integral de tickets vigía en colas de mensajes y manejo de errores en callbacks de Telegram.
