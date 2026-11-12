# Changelog — Gamma Bot

Todas las modificaciones notables de este proyecto serán documentadas en este archivo.
El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.1.5] - 2026-11-12

### Seguridad
* **Autenticación *Fail-Closed* en API y Webhooks (`src/api/security.py`):**
  * Eliminación de valores por defecto de desarrollo en `is_valid_api_key()` e `is_valid_webhook_secret()`, garantizando rechazo inmediato (`401 Unauthorized`) si las claves de entorno no están definidas en cualquier entorno.

### Añadido
* **Control de Activación/Desactivación de Módulos (`src/config.py`, `src/api/v1/routes_webhooks.py`, `src/api/v1/routes_capacidades.py`, `src/app_queue/worker.py`):**
  * Nuevas funciones `is_module_enabled(module_name)` y `get_disabled_modules()` con soporte para `ENABLE_<MODULO>` y `DISABLED_MODULES`.
  * Módulo `whatsapp` desactivado por defecto (`ENABLE_WHATSAPP=false`), retornando `503 MODULE_DISABLED` en `/api/v1/webhooks/whatsapp` cuando se encuentra apagado y omitiendo la exigencia de `WHATSAPP_WEBHOOK_SECRET` en `validate_production_config()` hasta su habilitación explícita.
  * Exposición del estado `"whatsapp_webhook_enabled"` en `GET /api/v1/capacidades` y filtrado dinámico de módulos deshabilitados.

---

## [2.1.4] - 2026-11-11

### Añadido
* **Endpoint de Auto-Descubrimiento de la API (`GET /api/v1/capacidades`):**
  * Nuevo módulo [`src/api/v1/routes_capacidades.py`](file:///e:/PG/vcp-s/Gamma_bot/src/api/v1/routes_capacidades.py) con introspección dinámica de `current_app.url_map`.
  * Catálogo completo de rutas activas de `/api/v1`, métodos HTTP soportados, docstrings descriptivos, argumentos dinámicos y flags de `capacidades_clave`.
  * Filtro opcional por módulo `?modulo=<nombre>` (ej. `?modulo=presupuesto`).
  * Esquemas Pydantic formales [`RutaEndpointInfo`](file:///e:/PG/vcp-s/Gamma_bot/src/api/schemas.py) y [`CapacidadesResponse`](file:///e:/PG/vcp-s/Gamma_bot/src/api/schemas.py).

### Optimizado
* **Calibración Dimensional de ReportLab para Hoja Única A4 (`src/logic/pdf_service.py`):**
  * Márgenes calibrados a 1.0 cm (alto útil expandido a 785.20 pt).
  * Banner superior unificado A1:G1 (20 pt) y fila compacta de subtítulo y metadata de emisión Asunción (16 pt).
  * Padding vertical de celdas optimizado a 2.2 pt para tablas mensuales de hasta 31 días corridos más cuadro resumen de facturación con IVA (136 pt).
  * Certificación empírica mediante test unitario [`tests/test_pdf_a4_fit.py`](file:///e:/PG/vcp-s/Gamma_bot/tests/test_pdf_a4_fit.py) garantizando `TOTAL_PAGINAS_GENERADAS == 1` con ocupación del 92.4% y 2.10 cm de margen libre de seguridad (`INV-A4`).
* **Estandarización de Etiquetas Canónicas de Liquidación (`src/logic/logic.py`, `src/services/excel_service.py`):**
  * Unificación de etiquetas de facturación a: `Horas del mes`, `Monto por hora`, `Total Monto por Horas`, `IVA 10%`, `TOTAL IVA INCLUIDO`, `TOTAL FACTURA`.
  * Filtro defensivo anti-duplicación actualizado para tolerar nombres anteriores y nuevos en re-ejecuciones de cierre.

---

## [2.1.3] - 2026-11-10

### Añadido
* **Acceso y Gestión de Presupuesto Base (`src/repositories/sheets_repository.py`, `src/api/v1/routes_presupuesto.py`, `src/api/schemas.py`):**
  * **Eliminación de Gastos Fijos:** Nuevo método `eliminar_gasto_fijo(concepto)` en `SheetsRepository` y `AgenteFinanciero`, y endpoint REST `DELETE /api/v1/presupuesto/fijos/<concepto>` protegido por `X-API-KEY`.
  * **Configuración de Techos Presupuestarios Variables:** Nuevo esquema `TechoPresupuestarioUpdate` y endpoint REST `PUT /api/v1/presupuesto/techos/<categoria>` con persistencia dual en `LocalRepository` (`PRESUPUESTO_TECHO_<CAT>` y `PRESUPUESTO_UMBRAL_<CAT>`) y sincronización en celda de `Presupuesto_Base`.
  * **Blindaje Defensivo de `Obligaciones_Maestro`:** Manejo retrocompatible de columnas obsoletas (`Cuotas` legacy autocompletada con `Cuotas_Totales` y `Event_ID` con `""`), desacoplando clientes móviles de campos legados sin corrimientos columnares en Google Sheets.
  * **Especificación y Contratos para Gamma Mobile (`docs/specs/paridad-presupuesto-obligaciones-mobile/`):**
    * Actualización canónica de `docs/ESPECIFICACIONES_API_MOBILE.md` y `docs/especificacion_gamma_mobile_android.md`.
    * Diseño completo de UI/UX para `PresupuestoScreen` en Jetpack Compose (Salario Base editable, Gastos Fijos por categoría con edición/borrado, y Monitor de Techos de Consumo Variable con barras de progreso y semáforo de estado).
    * Creación de `docs/SYSTEM_MAP.md` como inventario de verdad del sistema e invariantes de gobernanza.

---

## [2.1.2] - 2026-11-09

### Añadido
* **Modo de Edición de Asistencia Protegido por X-API-KEY (`src/com/handlers/asistencia.py`, `src/services/asistencia_service.py`):**
  * **Flujo interactivo en Telegram:** Nuevo comando `/editar` (y alias `/editar_asistencia`) y botón inline *"✏️ Modo Edición"* dentro de `/horas`.
  * **Privacidad y Seguridad:** Desafío de autenticación solicitando la `X-API-KEY`. El bot elimina de inmediato el mensaje con la clave (`bot.delete_message`) para prevenir filtraciones en el historial del chat, y valida con `is_valid_api_key` en tiempo constante.
  * **Acción rápida de limpieza:** Botón inline *"🔄 Limpiar salida de hoy"* para anular salidas accidentales o prematuras en SQLite (`hora_salida = None`), vaciar la celda en Google Sheets y dejar la jornada en estado TRABAJANDO para marcar normalmente al retirarse.
  * **Rectificación guiada por fecha:** Opciones para rectificar *"📅 Ayer"* o ingresar cualquier fecha (`YYYY-MM-DD`) con parseo determinista de tramos y sincronización forzada write-through a Google Sheets.
  * **Especificación para Gamma Mobile (`docs/specs/modo-edicion-asistencia/spec.md`):** Arquitectura y contratos para la tarjeta del reloj con botón candado 🔒 y selectores `TimePicker`.

---

## [2.1.1] - 2026-11-05

### Corregido
* **Aislamiento de Spreadsheets y Remediación de SyncService (`src/services/sync_service.py`, `src/api/v1/routes_asistencia.py`):**
  * **Problema resuelto:** Eliminado el fallback erróneo `LIBRO_CONTABLE_ID` de `SyncService` y del endpoint `/asistencia/marcar`, que provocaba la creación indebida de pestañas laborales en el libro contable. Se garantiza el uso exclusivo de `SPREADSHEET_ID` para asistencia laboral y `SPREADSHEET_MATERIAS_ID` para cátedras.
  * **Búsqueda secuencial determinista:** Eliminado el uso de `append_row` (que saltaba a la fila 61); se escanea el rango operativo de filas 2 a 40 respetando la fórmula dinámica `=SI(...)` en Columna G y aplicando `value_input_option="USER_ENTERED"`.
  * **Auto-sincronización defensiva post-deploy:** Hook en `src/flask_app.py:deploy()` para conciliar automáticamente las jornadas con `forzar=True`.
  * **Supresión de error 400 en soporte Telegram:** Manejo seguro de `ApiTelegramException` por "message is not modified" en `src/com/handlers/soporte.py`.

### Añadido
* **Endpoint de Rectificación de Jornada Laboral (`src/api/v1/routes_asistencia.py`, `src/api/schemas.py`):**
  * Nuevo endpoint autenticado `PUT /api/v1/asistencia/jornadas/<fecha>` para actualizar horarios históricos o del día en SQLite (`gamma_local.db`) con recálculo automático de `horas_decimal` y volcado inmediato write-through a Google Sheets, garantizando reportes e impresiones de fin de mes consistentes.

---

## [2.1.0] - 2026-11-05

### Corregido
* **Desacoplamiento Matemático de Margen Libre (`src/logic/financiero.py`, `src/api/v1/routes_dashboard.py`, `src/api/v1/routes_proyectos.py`):**
  * **Problema resuelto:** Los gastos operativos cotidianos del Libro Diario estaban reduciendo indebidamente el margen libre disponible mensual (`margen_libre`), desvirtuando su propósito de métrica de capacidad estructural y horizonte de endeudamiento. Adicionalmente, existía un fallback empírico viciado `max(0, flujo_neto - int(gastos * 0.2))` en el endpoint de dashboard.
  * **Solución aplicada:** Se redefinió la fórmula canónica de Margen Libre: $\text{MLD} = \text{Ingreso Base} - \text{Gastos Fijos} - \sum \text{Cuotas Activas con } (\text{Es\_Gasto\_Fijo} = 1)$. Los gastos operativos del Libro Diario solo impactan el saldo acumulado en caja (`saldo_acumulado`), manteniendo el margen libre como un indicador estructural estable e inmune a compras diarias. Se eliminaron los fallbacks viciados en los endpoints de dashboard y proyectos.

### Añadido
* **Atributo Booleano `Es_Gasto_Fijo` en Obligaciones (`Obligaciones_Maestro`):**
  * Columna 17 (`Es_Gasto_Fijo`) agregada en `ENCABEZADOS_OBLIGACIONES_MAESTRO` (`src/logic/constants.py`).
  * Soporte en esquemas Pydantic v2 `ObligacionCreate`, `ObligacionUpdate` y `ObligacionResponse` (`src/api/schemas.py`) con default `True` (`1`).
  * Alternancia dinámica automática en capa de persistencia (`src/repositories/sheets_repository.py`) y endpoints REST (`src/api/v1/routes_obligaciones.py`): al pausar una obligación (`Estado == "Pausado"` o `"Pausada"`), `Es_Gasto_Fijo` conmuta automáticamente a `0` liberando inmediatamente su cuota del margen libre; al reactivar a `"Activo"`, se restablece a `1`.
  * Retrocompatibilidad nativa en `SheetsRepository.get_todas_obligaciones()` infiriendo dinámicamente `1` para deudas activas preexistentes sin la columna 17 poblada en Google Sheets.

---

## [2.0.0] - 2026-11-04

### Corregido
* **Sincronización Inmediata Write-Through de Asistencia Laboral (`src/logic/logic.py`):**
  * **Incidente detectado:** Al refactorizar a la arquitectura *Local-First* con SQLite (`LocalRepository`), `AgenteAutonomoHoras.ejecutar_marcado_para_bot` y `ejecutar_corte_automatico` actualizaban la tabla `asistencia_laboral` con `sincronizado_sheets = 0`, pero `SyncService.volcar_local_a_sheets` sólo estaba disponible como invocación manual en `POST /api/v1/asistencia/sync`. Esto provocaba que las marcaciones (vía Telegram o API REST) quedaran en SQLite sin reflejarse en la pestaña correspondiente de Google Sheets (ej. `Horas_Noviembre_2026`).
  * **Solución aplicada:** Se implementó sincronización inmediata *write-through* en `src/logic/logic.py`. Tras la inserción en SQLite, se ejecuta el volcado a Google Sheets marcando `sincronizado_sheets = 1`. Si la API de Google Sheets no está disponible o sufre rate limit, se captura defensivamente la excepción manteniendo el registro seguro en SQLite para su posterior sincronización sin bloquear al usuario.

### Añadido
* **Paridad Funcional Backend API v2 para Gamma Mobile (Fase 6):**
  * Nuevos esquemas Pydantic v2 en `src/api/schemas.py` para Presupuesto, Techos, Proyectos, Estado de Jornada y Bootstrap.
  * Nuevo Blueprint `presupuesto_bp` (`src/api/v1/routes_presupuesto.py`) con endpoints `GET /presupuesto/fijos`, `PUT /presupuesto/fijos/<concepto>`, `POST /presupuesto/fijos`, `PUT /presupuesto/salario-base` y `GET /presupuesto/techos`.
  * Nuevo Blueprint `proyectos_bp` (`src/api/v1/routes_proyectos.py`) con endpoints `POST /proyectos/simular` y `POST /proyectos/<id_proyecto>/aprobar`.
  * Nuevo endpoint `GET /api/v1/asistencia/estado-hoy` en `src/api/v1/routes_asistencia.py` para consulta de reloj diario sin mutación (`PENDIENTE`, `TRABAJANDO`, `COMPLETADO`, `LIBRE`).
* **Motor Proyector de Flujo de Caja a 30 Días (Fase 5):**
  * Implementado `CashFlowProjector` (`src/services/cashflow_service.py`) con simulación temporal diaria, imputación de compromisos bancarios de `Obligaciones_Maestro`, proyección de consumo variable diario y detección proactiva de días críticos con saldo negativo o iliquidez.
  * Nuevo endpoint REST `GET /api/v1/proyecciones/flujo-caja` en `src/api/v1/routes_proyecciones.py` con DTOs `FlujoCajaResponse` y `FlujoCajaItemDiario`.
* **Alertas Presupuestarias Proactivas Multi-Canal con Cooldown (Fase 5):**
  * Función `despachar_alerta_presupuestaria_proactiva` (`src/services/presupuesto_service.py`) con encolado asíncrono y control de cooldown en memoria de 24h por categoría y destinatario para Telegram y WhatsApp.
* **Adaptador Push y Registro de Dispositivos Gamma Mobile (Fase 5):**
  * `PushNotificationAdapter` implementando `INotificationPort` con persistencia atómica en `data/dispositivos_push.json`, auto-registro de canal push en el dispatcher y endpoints REST `POST /api/v1/dispositivos/registrar`, `GET /api/v1/dispositivos` y `POST /api/v1/dispositivos/notificar`.
* **Parser Financiero Conversacional de Lenguaje Natural (Fase 4):**
  * Motor determinista `FinanceNLParser` (`src/utils/nlp_parser.py`) con regex de alto rendimiento para extraer montos (separadores paraguayos, multiplicadores `k`/`M`, divisas), tipos de movimiento, categorías y comercios reconocidos en <5 ms.
  * Endpoint REST `POST /api/v1/movimientos/parse` para integración directa con interfaces móviles.
  * Integración en el worker para registro automático de finanzas desde mensajes libres de WhatsApp con confirmaciones enriquecidas.
* **Hardening y Rate Limiting en Webhooks (Fase 4):**
  * Centralización de `limiter` en `src/api/security.py` con resolución segura de proxies (`X-Forwarded-For`), límite de 60 req/min y límite de carga útil de 64 KB (`HTTP 413`) en `POST /api/v1/webhooks/whatsapp`.
* **Canal WhatsApp y Webhooks Asíncronos Desacoplados (Fase 3):**
  * `WhatsAppNotificationAdapter` sobre API REST de WhatsApp / Evolution API, saneamiento telefónico en formato canónico E.164 (`src/utils/phone_utils.py`) y encolado desacoplado en `cola.db`.
* **Despachador Omnicanal Agnóstico y Migración de Cola (Fase 2):**
  * Interfaz canónica `INotificationPort` (`src/ports/notification_port.py`) y orquestador `NotificationDispatcher` (`src/services/notification_dispatcher.py`).
  * Migración no destructiva de `cola.db` con soporte de `recipient_id` alfanumérico y columna `channel`.
* **Arquitectura Modular API REST y Persistencia Local Dual (Fase 1):**
  * Descomposición integral de la API REST en submódulos bajo `src/api/v1/*` orquestados en `v1_bp`.
  * Capa de persistencia local SQLite (`src/repositories/local_repository.py`) con modo WAL y latencia < 15ms.
  * Endpoint climático para Asunción con alerta preventiva de lluvia (`GET /api/v1/clima`).
  * DTO puro `MarcacionResult` y homogenización de asientos contables de amortización de pasivos en `src/logic/financiero.py`.

---

## [1.18.6] - 2026-10-30

### Corregido
* **Integridad Contable y Paridad Backend con Gamma Mobile (`HANDOFF-backend.md` Módulos 3.1, 5 y 6):**
  * **Corrección de Duplicación de `saldo_inicial` (Módulo 6):** En `src/logic/financiero.py` se definió $\text{flujo\_neto} = \text{total\_ingresos} - \text{total\_gastos}$ (operativo) y $\text{saldo\_acumulado} = \text{saldo\_inicial} + \text{flujo\_neto}$, eliminando la doble suma del saldo inicial en `GET /api/v1/dashboard/summary` ([src/api/blueprint.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/blueprint.py)) y en el proyector de capacidad de pago.
  * **Blindaje Estructural de Encabezados (Módulo 5.1):** En `SheetsRepository._ensure_headers` ([src/repositories/sheets_repository.py](file:///e:/PG/vcp-s/Gamma_bot/src/repositories/sheets_repository.py)) se bloquea cualquier sobrescritura destructiva de celdas si la aridad de la cabecera no coincide con la longitud de columnas esperada y existen filas de datos, previniendo desfasajes horizontales.
  * **Migración Idempotente de `Obligaciones_Maestro` (Módulo 5.2):** Creado script `scripts/migrar_obligaciones_maestro.py` con `--dry-run` y `--apply` para realinear filas legacy de 15 columnas o filas desfasadas a las 16 columnas canónicas de `ENCABEZADOS_OBLIGACIONES_MAESTRO`.
  * **Ejecución Real de Cierres vía API (Módulo 3.1):** En `POST /api/v1/cierres/ejecutar` ([src/api/blueprint.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/blueprint.py)) se eliminaron las constantes hardcodeadas (160h, 4.5M Gs), conectando el endpoint al cómputo real de analíticas de asistencia ([src/logic/logic.py](file:///e:/PG/vcp-s/Gamma_bot/src/logic/logic.py)) y balances de Libro Diario ([src/logic/financiero.py](file:///e:/PG/vcp-s/Gamma_bot/src/logic/financiero.py)), generando PDFs y reportes históricos fidedignos.

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
