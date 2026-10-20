# Technical Research & Decisions (Research) — Integración GammaMobile v0.0.9

**Fecha:** 2026-10-20  
**Feature:** `integracion-gammamobile-v009`  
**Estado:** Resuelto (Fase 0 Completa)

---

## 1. Decisiones Técnicas y Arquitectónicas

### Decisión 1: Integración de Marcación con `AgenteAutonomoHoras.ejecutar_marcado_para_bot`
- **Contexto:** El endpoint `POST /api/v1/asistencia/marcar` retornaba respuestas falsas y estáticas.
- **Decisión:** 
  1. Instanciar `AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)` y delegar en `ejecutar_marcado_para_bot(modo=modo)`.
  2. Parsear el string de retorno: si comienza con `"❌"` o `"⚠️"`, retornar código HTTP 400 (Bad Request) o 409 (Conflict) indicando el error de validación retornado por la lógica de negocio.
  3. Si la marcación fue aceptada, determinar si fue `"entrada"` o `"salida"` buscando patrones en el texto y retornar código HTTP 200 con la hora real.
- **Alternativas descartadas:**
  - *Reescribir la lógica de marcación dentro de blueprint.py:* Descartado para evitar duplicación de código y garantizar consistencia entre el Bot de Telegram y la App Móvil.

### Decisión 2: Pipeline Tributario e Invalidation de Caché en Dashboard Summary
- **Contexto:** Al insertar movimientos vía API, no se calculaban las columnas de desglose IVA ni se forzaba la invalidación de caché.
- **Decisión:**
  1. Resolver `spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""`.
  2. En `POST /api/v1/movimientos`, aplicar la fórmula tributaria de Paraguay (IVA 10% $\rightarrow$ Base $Total / 1.1$, IVA $Total - Base$; IVA 5% $\rightarrow$ Base $Total / 1.05$, IVA $Total - Base$; Exento $\rightarrow$ Base $Total$, IVA 0) antes de persistir en `Libro_Diario`.
  3. En `GET /api/v1/dashboard/summary`, calcular `margen_libre = calcular_margen_de_ataque()` dinámico e inyectar cabeceras HTTP `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` y `Pragma: no-cache`.
- **Alternativas descartadas:**
  - *Mantener un caché intermedio en memoria de Flask:* Descartado porque la app móvil ya cuenta con caché local offline-first en Room y requiere que las consultas directas al servidor reflejen los datos más frescos.

### Decisión 3: Conexión Real con Google Calendar y CRUD Completo de Avisos
- **Contexto:** `POST` y `DELETE` solo modificaban `src/avisos.json` y no sincronizaban con Calendar. `GET` fallaba en runtime por incompatibilidad de firma y método.
- **Decisión:**
  1. Corregir llamada en `GET /api/v1/avisos`: pasar `spreadsheet_id` y llamar al método real `obtener_lista_avisos_calendar()`.
  2. En `POST /api/v1/avisos`: admitir `repeticion` y `hitos_minutos`. Si las credenciales de Google Calendar están activas, invocar `agente_horas.guardar_aviso_calendar(...)` para crear el evento y registrar el `event_id` resultante en el JSON de avisos. Si Calendar falla o está offline, respaldar en `src/avisos.json` de forma tolerante.
  3. Implementar `PUT /api/v1/avisos/<aviso_id>`: actualizar los datos en `src/avisos.json` y, si contiene `event_id`, recrear o actualizar el evento en Google Calendar.
  4. En `DELETE /api/v1/avisos/<aviso_id>`: eliminar de `src/avisos.json` y, si tiene `event_id`, invocar `agente_horas.eliminar_aviso_calendar(event_id)`.
- **Alternativas descartadas:**
  - *Crear una tabla separada en Google Sheets para avisos:* Descartado para mantener simplicidad y respetar la arquitectura dual existente (`avisos.json` para metadatos locales y Google Calendar como motor de eventos).

### Decisión 4: Soporte Integral para Deudas Simuladas y CRUD en Sheets
- **Contexto:** `POST /api/v1/obligaciones` forzaba estado Activo, no existían rutas de modificación/eliminación, y la simulación usaba un margen hardcodeado.
- **Decisión:**
  1. Actualizar `ObligacionCreate` en `src/api/schemas.py` para aceptar `estado` (`"Activo"` o `"Simulado"`), `entidad`, `cuotas_totales`, `cuotas_restantes`, `cuota_referencia_gs`, `dia_vencimiento`, `fecha_inicio`, `observaciones`.
  2. Implementar `PUT /api/v1/obligaciones/<obligacion_id>`: permitir actualizar el estado (ej. pasar de `"Simulado"` a `"Activo"` al aprobar), saldo y cuotas en la hoja `Obligaciones_Maestro` de `SheetsRepository`.
  3. Implementar `DELETE /api/v1/obligaciones/<obligacion_id>`: añadir método `delete_obligacion` en `SheetsRepository` que busque y elimine la fila correspondiente en la hoja `Obligaciones_Maestro`.
  4. En `POST /api/v1/obligaciones/simular`: invocar `calcular_margen_de_ataque()` dinámicamente para obtener el margen libre real antes de diagnosticar la viabilidad.
- **Alternativas descartadas:**
  - *Guardar las obligaciones simuladas en un archivo temporal:* Descartado; la hoja `Obligaciones_Maestro` soporta la columna `Estado` permitiendo registrar `"Simulado"` y `"Activo"` sin romper los cálculos de deuda activa.

### Decisión 5: Lectura en Reversa de Logs del Sistema
- **Contexto:** `GET /api/v1/sistema/logs` devolvía datos ficticios.
- **Decisión:**
  1. Leer directamente las últimas líneas de `src/gen_log.txt` (archivo gestionado por `src/logger_config.py`).
  2. Utilizar un parser regex que extraiga la fecha/hora entre corchetes `[YYYY-MM-DD HH:MM:SS]` o `[DD/MM/YYYY HH:MM:SS]`, detecte el nivel (`ERROR`, `WARNING`/`WARN`, o `INFO`), y extraiga el mensaje.
  3. Invertir el orden para retornar los eventos más recientes primero (`order: desc`) y limitar la salida según el parámetro query `?limit=N` (por defecto 20, máximo 100).
- **Alternativas descartadas:**
  - *Configurar un servidor Elasticsearch o servicio externo de logging:* Sobredimensionado para el perfil WSGI en PythonAnywhere.
