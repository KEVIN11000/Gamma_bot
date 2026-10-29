# Changelog — Gamma Bot

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.18.5] - 2026-10-29

### Añadido
* **Paridad Integral y Optimización con Gamma Mobile (`v0.0.12` / `HANDOFF-backend.md`):**
  * `MovimientoCreate` ([src/api/schemas.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/schemas.py)): Soporte nativo de alias `"tipo"` (`movimiento`) y `"monto"` (`total`) con `populate_by_name=True`, garantizando que los ingresos móviles no se registren como gastos.
  * Desempaquetado plano de `deuda_foco` en la raíz de `GET /api/v1/obligaciones/foco` para compatibilidad directa con DTOs de Android.
  * Paridad dual de claves (`"tipo"` y `"tipo_movimiento"`) en los servicios de IA y OCR ([src/logic/ai_service.py](file:///e:/PG/vcp-s/Gamma_bot/src/logic/ai_service.py)).
  * Respuesta estructurada `HTTP 200 OK` con `tipo: "info"` en `POST /api/v1/asistencia/marcar` cuando la jornada ya fue registrada.
  * Invalidación reactiva de `_sheets_cache` al insertar movimientos para reflejar saldos de inmediato en el dashboard.
  * Deduplicación e idempotencia por `client_id` (vía JSON o header `X-Client-Id`) con ventana de 24 horas.
  * Cálculo estricto de horas trabajadas y salario MTD en `AgenteAutonomoHoras.calcular_analiticas_asistencia` exigiendo salida confirmada.
  * Endpoint `GET /api/v1/asistencia/cierres` para consultar períodos laborales archivados.

## [1.18.4] - 2026-10-29

### Añadido
* **Auto-eliminación de Botoneras y Mensajes Efímeros en Telegram (`TG-fc5352bf`):**
  * Utilitarios centralizados en `src/com/core/utils.py`: `remover_teclado_inline` (`edit_message_reply_markup(reply_markup=None)`) y `eliminar_mensaje_seguro` con captura defensiva de excepciones de Telegram API (`message to delete not found`, `message is not modified`, `message can't be deleted`).
  * Protección contra colisiones y accesos concurrentes en `pending_deletions.json` mediante `threading.Lock`.
  * Integración en handlers de navegación (`base.py`) y finanzas/fijos (`finanzas.py`) para neutralizar botoneras de acción y evitar clics duplicados en el chat.
  * Preservación intacta de mensajes informativos y comprobantes contables/laborales definitivos.

## [1.18.3] - 2026-10-28

### Corregido
* **Resiliencia en Cierre Contable y Backup de Contingencia (`DriveService`):**
  * Implementada la subida de backups a Google Drive v3 con credenciales de servicio y liberación adecuada de descriptores de archivo en entornos Windows.
  * Añadido fallback determinista a almacenamiento local seguro (`src/data/backups/`) cuando la API de Google Drive no está disponible o falla la red, evitando la interrupción indebida de `/cierre_mensual` y garantizando la persistencia del archivo CSV.
  * Corregida la ruta duplicada `UNIFIED_TICKETS_FILE` en `src/com/handlers/soporte.py` (`BASE_DIR / "data" / "tickets.json"`), resolviendo la excepción `FileNotFoundError: /src/src/data/tickets.json`.

## [1.18.2] - 2026-10-28

### Corregido
* **Robustez de Tipado Estático y Paridad CI Ubuntu/Linux:**
  * Reforzada la guarda de tipos en `asistencia_service.py` (`procesar_comando_horas`) para estrechar `Optional[Dict[str, Any]]` y garantizar indexación segura ante `mypy`.
  * Anotación explícita de tipos (`dict[str, Any]`, `list[Any]`) en fixtures de `tests/test_soporte.py`.
  * Verificación y pase en verde del 100% de los chequeos de `mypy --no-site-packages` en 70 archivos sin errores.

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
