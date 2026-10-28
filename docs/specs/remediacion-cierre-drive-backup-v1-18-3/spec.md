# Especificación Funcional: Remediación de Cierre Mensual, Backup Drive y Sincronización de Soporte (v1.18.3)

## 1. Contexto del Incidente
- **Ticket asociado:** `TICKET-TG-4006aa8e` (Reportado el 28/10/2026 12:31:56 -03:00 por `@Kl4lT0`).
- **Estado en Vigía:** `in_progress`.
- **Síntoma primario en Telegram:**
  > "❌ Error al ejecutar el cierre: Fallo al generar el backup en Google Drive para el período 10/2026. El cierre mensual fue abortado sin modificar Libro Diario."
- **Síntoma secundario en telemetría de servidor (`server_log.txt`):**
  > `[2026-10-28 12:31:18] DriveService.upload_backup no implementado — backup local únicamente`
  > `[2026-10-28 12:31:56] No se pudo sincronizar ticket con tickets.json: [Errno 2] No such file or directory: '/home/kevin11000/mysite/src/src/data/tickets.json'`

---

## 2. Alcance (In-Scope)

1. **Resiliencia en Cierre Contable Mensual (`src/logic/financiero.py`):**
   - El proceso de cierre (`ejecutar_cierre_mensual`) no debe quedar bloqueado o abortado de forma fatal si Google Drive no está disponible o devuelve un identificador de contingencia.
   - Si la subida a Drive devuelve un ID de archivo local o de contingencia (ej. `local_backup_<timestamp>`), el cierre contable debe completarse exitosamente registrando la trazabilidad del backup en `Archivo_Backup_Drive` y preservando el archivo local en el directorio de backups.
2. **Implementación Funcional de `DriveService.upload_backup` (`src/services/drive_service.py`):**
   - Implementar la subida efectiva a Google Drive utilizando las credenciales existentes en `credentials.json` (que ya tienen el scope `https://www.googleapis.com/auth/drive`).
   - Implementar un fallback seguro y transparente: si las credenciales de Drive no son válidas, no hay conexión de red o la API de Drive arroja un error transitorio, persistir el backup en una carpeta local estandarizada `data/backups/` y retornar un identificador de contingencia `local:<hash_o_nombre>`, emitiendo un log de advertencia sin lanzar excepciones no controladas.
3. **Corrección de Ruta Duplicada en Soporte (`src/com/handlers/soporte.py`):**
   - Corregir `UNIFIED_TICKETS_FILE`: actualmente configurado como `BASE_DIR / "src" / "data" / "tickets.json"`, donde `BASE_DIR` ya apunta a `src/`, generando la ruta inexistente `/src/src/data/tickets.json`. Debe apuntar a `BASE_DIR / "data" / "tickets.json"`.
4. **Verificación y Pruebas Unitarias:**
   - Pruebas unitarias de `DriveService.upload_backup` verificando:
     - Subida exitosa a Google Drive (mock de API de Google Drive v3).
     - Manejo de fallback local cuando la API falla o `credentials.json` no existe.
   - Pruebas de `ejecutar_cierre_mensual` validando que se complete con backup Drive o backup local de contingencia.
   - Pruebas de guardado de tickets en `src/com/handlers/soporte.py` confirmando la ruta correcta de `tickets.json`.

---

## 3. Fuera de Alcance (No-Scope)

- Modificación de las reglas contables o fórmulas de cálculo de impuestos (IVA Débito/Crédito, Saldo Acumulado, Margen Libre).
- Modificaciones en la interfaz o contratos de endpoints de la app móvil GammaMobile.
- Alteración de las pestañas preexistentes en Google Sheets.

---

## 4. Criterios de Aceptación (DoD)

1. **Ejecución exitosa de `/cierre_mensual`:**
   - La ejecución de `/cierre_mensual 10 2026` debe completarse sin arrojar `RuntimeError`, registrando la fila correspondiente en `Cierres_Historicos` y reseteando `Libro_Diario` con el saldo inicial.
2. **Backup garantizado:**
   - Existe siempre un archivo CSV respaldado ya sea en Google Drive (retornando su `file_id`) o en `data/backups/` (retornando `local:backup_YYYY_MM.csv`).
3. **Telemetría sin errores de ruta:**
   - El registro de un ticket vía `/soporte` escribe correctamente en `src/data/tickets.json` sin arrojar `FileNotFoundError: /src/src/data/tickets.json`.
4. **Calidad de código y suites:**
   - 100% tests pasando en `pytest` (219+ tests).
   - `black`, `flake8` y `mypy --no-site-packages` limpios con 0 advertencias.
