# Registro de Incidentes (Incident Log)

Este documento registra errores, comportamientos inesperados y "trampas" de despliegue para evitar que vuelvan a ocurrir en el futuro.

## Incidente 001: Pérdida de estado y fallas de autenticación por refactor a `src-layout`

- **Fecha:** 10 de Septiembre de 2026
- **Síntomas:**
  - El bot arrojaba errores de autenticación con Google Sheets, a pesar de haber renovado el archivo `credentials.json`.
  - El bot empezó a registrar horas en una pestaña nueva llamada "Mayo 2026" (comportamiento por defecto) en lugar del período real que venía operando.
- **Causa Raíz:**
  - Tras refactorizar la arquitectura del proyecto moviendo el código operativo a una carpeta `src/` (patrón src-layout), la variable base del sistema (`BASE_DIR`) cambió.
  - El código empezó a buscar todos los archivos críticos (`credentials.json`, `.env`, `periodo_actual.txt`, `estado_temporal.db`) adentro de `src/`.
  - En el servidor de producción (y localmente), estos archivos habían quedado "huérfanos" en la carpeta raíz del proyecto, por lo que el bot los ignoraba completamente, asumiendo que no existían.
- **Solución:**
  - Se movieron físicamente los archivos de estado y credenciales desde la raíz a la carpeta `src/`.
- **Lección Aprendida / Regla de despliegue:**
  - Todos los archivos secretos e ignorados por Git (`.env`, `credentials.json`, `periodo_actual.txt`, `estado_temporal.db`, `gen_log.txt`) **deben** residir obligatoriamente en `src/`. NUNCA dejarlos en la raíz.
