# Especificación Funcional (Spec) — Integración Core Gamma_bot con GammaMobile v0.0.9

**Fecha:** 2026-10-20  
**Proyecto:** `Gamma_bot` (Backend Core — Flask API / WSGI / Google Sheets / Google Calendar)  
**Feature:** `integracion-gammamobile-v009`  
**Referencia móvil:** `GammaMobile v0.0.9` (`repositories/Main-stable/docs/specs/GammaMobile v0.0.9/requerimientos_gamma_bot.md`)

---

## 1. Alcance y Casos de Uso

### CU-01: Marcación Laboral Real en Google Sheets (`POST /api/v1/asistencia/marcar`)
- **Situación actual:** El endpoint en `src/api/blueprint.py` devuelve un JSON estático simulado sin interactuar con Google Sheets ni invocar al `AgenteAutonomoHoras`.
- **Comportamiento esperado:**
  - El endpoint recibe `modo` (`"normal"` o `"directo"`).
  - Resuelve `spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID")`.
  - Invoca `AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id).ejecutar_marcado_para_bot(modo=modo)`.
  - Evalúa la respuesta del agente:
    - Si el mensaje retornado inicia con `"❌"` o `"⚠️"` o contiene advertencias/errores semánticos de validación, retorna código HTTP `400` o `409` con `{"tipo": "error", "mensaje": mensaje_error}`.
    - Si la marcación fue exitosa, parsea el tipo (`"entrada"` o `"salida"`), extrae la hora registrada (`HH:MM`) y retorna código HTTP `200` con `{"tipo": tipo, "hora": hora, "mensaje": mensaje_confirmacion}`.
  - En caso de error inesperado o indisponibilidad de red con Google Sheets, maneja la excepción sin colgar el worker y responde HTTP `502` / `500` estructurado.

### CU-02: Pipeline Dinámico de Balance, Margen Libre y Posición IVA (`GET /api/v1/dashboard/summary` y `POST /api/v1/movimientos`)
- **Situación actual:**
  - `GET /dashboard/summary` lee `SPREADSHEET_ID` exclusivamente con fallback a `"dummy_sheet_id"`, ignorando `LIBRO_CONTABLE_ID`.
  - `POST /movimientos` inserta directamente en `Libro_Diario` omitiendo el cálculo estandarizado de columnas tributarias (`Monto_Gravado`, `Monto_IVA`, `Clasificacion_IVA`).
- **Comportamiento esperado:**
  - Unificar resolución de `spreadsheet_id` en todo `src/api/blueprint.py`: `os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""`.
  - En `POST /movimientos`, calcular las columnas fiscales (`Neto`, `IVA`, `Total`, `Tasa_IVA`, `Monto_Gravado`, `Monto_IVA`, `Clasificacion_IVA`) antes de insertar en Google Sheets para mantener sincronía inmediata con `AgenteFinanciero.obtener_balance()`.
  - En `GET /dashboard/summary`, calcular `margen_libre` llamando a `calcular_margen_de_ataque()` e incluir cabeceras de respuesta `Cache-Control: no-store, no-cache, must-revalidate` para garantizar reactividad en el cliente móvil.

### CU-03: Sincronización Real con Google Calendar y CRUD Completo de Avisos (`/api/v1/avisos`)
- **Situación actual:**
  - `GET /avisos` falla en runtime o lanza warning porque `AgenteAutonomoHoras` se llama sin `spreadsheet_id` y con método erróneo (`obtener_avisos_calendar` en vez de `obtener_lista_avisos_calendar`).
  - `POST /avisos` y `DELETE /avisos/<id>` solo modifican `src/avisos.json` y nunca crean/borran el evento en Google Calendar.
  - No existe ruta `PUT /api/v1/avisos/<id>` para actualizar avisos.
- **Comportamiento esperado:**
  - Corregir `GET /avisos`: instanciar `AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)` e invocar `obtener_lista_avisos_calendar()`.
  - En `POST /avisos`: aceptar campos extendidos `repeticion` (`"NINGUNA"`, `"DIARIA"`, `"SEMANAL"`, `"MENSUAL"`, `"ANUAL"`) y `hitos_minutos` (`list[int]`, hasta 5 hitos). Persistir en `src/avisos.json` y crear el evento en Google Calendar mediante `agente_horas.guardar_aviso_calendar(...)`.
  - Crear endpoint `PUT /api/v1/avisos/<aviso_id>`: actualizar título, fecha/hora, repetición e hitos en `src/avisos.json` y en Google Calendar (si existe `event_id` o recreando/actualizando el evento).
  - En `DELETE /api/v1/avisos/<aviso_id>`: eliminar de `src/avisos.json` y llamar a `agente_horas.eliminar_aviso_calendar(event_id)`.

### CU-04: Ciclo de Vida Completo de Deudas y Obligaciones (`/api/v1/obligaciones`)
- **Situación actual:**
  - `POST /obligaciones` fuerza `"Estado": "Activo"` e ignora si la app envía `"estado": "Simulado"`, `entidad`, `cuotas_totales`, etc.
  - No existen rutas `PUT /obligaciones/<id>` ni `DELETE /obligaciones/<id>`.
  - `POST /obligaciones/simular` evalúa viabilidad con un margen fijo hardcodeado de `2000000` ₲ en lugar del margen real.
- **Comportamiento esperado:**
  - Extender `ObligacionCreate` para recibir: `entidad`, `nombre`, `tipo`, `monto_inicial`, `saldo_actual`, `cuotas_totales`, `cuotas_restantes`, `cuota_referencia_gs`, `dia_vencimiento`, `fecha_inicio`, `estado` (`"Activo"` o `"Simulado"`), `observaciones`.
  - Crear endpoint `PUT /api/v1/obligaciones/<obligacion_id>`: permitir actualizar campos de la obligación (incluyendo aprobación de simulación cambiando estado a `"Activo"` y ajuste de cuotas/saldo) persistiendo en `SheetsRepository`.
  - Crear endpoint `DELETE /api/v1/obligaciones/<obligacion_id>`: eliminar el registro de obligación de la planilla `Obligaciones_Maestro` en `SheetsRepository` (y remover aviso de Calendar asociado si existe `Event_ID`).
  - En `POST /obligaciones/simular`: invocar `calcular_margen_de_ataque()` dinámico para obtener el `margen_actual` y evaluar viabilidad real (`Viable`, `Ajustado`, `Riesgo`).

### CU-05: Buffer de Registros y Logs Dinámicos del Servidor (`GET /api/v1/sistema/logs`)
- **Situación actual:** Devuelve 2 líneas JSON estáticas hardcodeadas.
- **Comportamiento esperado:**
  - Leer en reversa las últimas $N$ entradas (parámetro query `?limit=50`, por defecto 20, máximo 100) desde `src/gen_log.txt`.
  - Parsear cada línea extrayendo `timestamp`, `nivel` (`INFO`, `WARN`, `ERROR`) y `mensaje`.
  - Si el archivo no existe o está vacío, retornar fallback estructurado con el estado operativo del servicio.

---

## 2. Exclusiones Explícitas (No-Scope)
- **No modificar el cliente Android:** El repositorio `GammaMobile` ya completó y cerró su fase v0.0.9. No se tocará ningún archivo en `../GammaMobile`.
- **No romper handlers ni comandos de Telegram:** Todos los flujos conversacionales existentes (`/marcar`, `/balance`, `/obligaciones`, `/avisos`, etc.) deben seguir funcionando sin alteraciones.
- **No forzar dependencias pesadas innecesarias:** Se utilizará la infraestructura estándar de logging y parsing de Python sin introducir nuevos frameworks.
- **No eliminar el fallback síncrono para WSGI:** La política de despacho síncrono para PythonAnywhere se mantiene inalterada.
