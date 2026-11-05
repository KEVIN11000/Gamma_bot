# Especificación Funcional: Remediación de Escritura en SyncService y Gestión de Soporte

**ID de Incidente:** `TG-0b665c71`  
**Fecha:** 2026-11-05  
**Autor:** Antigravity (Pair Programming con @Kl4lT0)  
**Estado:** Fase 0 — Especificación Aprobada

---

## 1. Alcance y Contexto del Problema

### 1.1. Incidente Reportado
El usuario `@Kl4lT0` reportó mediante `/soporte`:
> *"Al parecer hay un error de escritura desde el módulo syncservice ya que no se reflejan las marcaciones desde la localdb en el servidor hasta el sheet"*
> *"ya me parecia raro que vi hoja de noviembre en el libro contable, está lógica puede cometer erroes"*

### 1.2. Diagnóstico Técnico y Evidencia Empírica de Logs
1. **Contaminación Cruzada Crítica (`LIBRO_CONTABLE_ID` vs `SPREADSHEET_ID`):**
   En `src/services/sync_service.py` (`SyncService.__init__`), se evaluaba:
   ```python
   self.spreadsheet_id = (
       spreadsheet_id
       or os.getenv("LIBRO_CONTABLE_ID")
       or os.getenv("SPREADSHEET_ID")
       or ""
   )
   ```
   Dado que `SyncService` se encarga exclusivamente de **Asistencia Laboral** y **Asistencia a Cátedras**, incluir `LIBRO_CONTABLE_ID` provocaba que ante cualquier instanciación por defecto se abriera la planilla financiera, creándose una pestaña "Noviembre 2026" en el libro contable y dejando la planilla de horas (`SPREADSHEET_ID`) completamente desatendida.
2. **Discrepancia en Ubicación de Filas (Append vs Fila Secuencial):**
   Al sincronizar un nuevo registro, el código invocaba `ws.append_row(fila_datos)` si la fecha no figuraba en la columna B. En Google Sheets con cuadrícula predeterminada de 60 filas, `append_row` coloca los registros en la fila 61, mientras que la cuadrícula operativa espera que se ocupen secuencialmente las filas 2 a 40 (ej: fila 11 para hoy tras la fila 10 del 4 de noviembre).
3. **Desalineación del Nombre de Hoja con `periodo_actual.txt`:**
   `AgenteAutonomoHoras` y los comandos de cierre usan `periodo_actual.txt` como la única fuente de verdad para la pestaña activa. `SyncService` construía `f"{MESES_ES[m - 1]} {y}"`, lo que generaba riesgo de crear hojas paralelas ante cierres anticipados o variaciones de nombre de mes.
4. **Manejo de Fórmulas y Modo de Entrada (`USER_ENTERED`):**
   `SyncService` actualizaba el rango sobrescribiendo la columna G con `0.0` durante marcaciones intermedias (destruyendo la fórmula dinámica `=SI(...)`) y utilizaba modo crudo (`RAW`).
5. **Excepción de Telegram API en `soporte.py`:**
   En `src/com/handlers/soporte.py:240`, cuando un usuario interactúa con las opciones de soporte sin modificar el texto, la API de Telegram arroja `ApiTelegramException: 400 Bad Request: message is not modified`.

---

## 2. Requerimientos Funcionales y Casos de Uso

### CU-01: Aislamiento Estricto de Dominios y Eliminación Total de `LIBRO_CONTABLE_ID`
- `SyncService` no debe tener ninguna referencia ni fallback hacia `LIBRO_CONTABLE_ID`.
- La asignación debe ser estrictamente:
  `self.spreadsheet_id = spreadsheet_id or os.getenv("SPREADSHEET_ID", "")`
- Si no está definido, debe fallar con error descriptivo (`ValueError`).

### CU-02: Posicionamiento Secuencial Determinista en Google Sheets
- Al sincronizar hacia Google Sheets:
  - Si la fecha ya existe en la columna B (normalizada con flexibilidad `DD/MM/YYYY`, `D/M/YYYY`, `YYYY-MM-DD`), se actualizan sus columnas correspondientes en esa fila.
  - Si la fecha NO existe en la columna B, el sistema buscará la primera fila vacía contigua (filas 2 a 40), insertará el día y la fecha en `A{fila}:B{fila}`, la fórmula matemática dinámica en `G{fila}` con `value_input_option="USER_ENTERED"`, y registrará las marcas horarias.
  - Se prohíbe el uso de `append_row`.

### CU-03: Alineación con `periodo_actual.txt`
- `SyncService` consultará `periodo_actual.txt` en `BASE_DIR` para determinar el nombre de la hoja laboral activa, garantizando total paridad con `AgenteAutonomoHoras`.

### CU-04: Preservación de Fórmulas en Columna G y Modo `USER_ENTERED`
- Para jornadas en curso (`horas_decimal == 0`), `SyncService` no sobreescribirá destructivamente la fórmula de la columna G.
- Todas las actualizaciones se harán con `value_input_option="USER_ENTERED"`.

### CU-05: Soporte de Reconciliación Forzada y Auto-Sync en Deploy
- `SyncService.volcar_local_a_sheets` soportará el parámetro `forzar: bool = False` o reconciliación de la jornada activa de hoy para reubicar registros que hayan quedado desplazados.
- En `flask_app.py`, el hook de `/deploy` invocará una sincronización automática tras el `git pull`.

### CU-06: Tolerancia a Fallos en Callback de Soporte
- `src/com/handlers/soporte.py` interceptará `ApiTelegramException` cuando contenga "message is not modified", eliminando la traza de error en los logs.

---

## 3. Criterios de Exclusión (No-Scope)
- No se alterarán los esquemas de tablas SQLite existentes.
- No se modificará la lógica de negocio de cálculo de horas de `AgenteAutonomoHoras.calcular_horas_jornada`.

---

## 4. Matriz de Impacto e Invariantes

| Invariante | Impacto | Verificación |
|---|---|---|
| Aislamiento Contabilidad vs Asistencia | Blindado: `SyncService` solo toca `SPREADSHEET_ID`. | `test_sync_service.py` |
| Persistencia SQLite Local-First | Intacta: los registros se guardan primero en local (`sincronizado_sheets=0`). | `test_local_repository.py` |
| Autenticación Fail-Closed | Intacta: no se alteran llaves ni validaciones de seguridad. | `test_auth_security.py` |
| Write-through no bloqueante | Intacta: errores remotos se capturan como advertencias sin interrumpir el bot. | `test_sync_service.py` |
