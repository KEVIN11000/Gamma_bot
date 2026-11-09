# Especificación Funcional: Modo de Edición de Asistencia Protegido por X-API-KEY

**Feature:** `modo-edicion-asistencia`  
**Fecha:** 2026-11-05  
**Canal Inicial:** Bot de Telegram  
**Canal Planificado:** App Móvil (Gamma Mobile)  
**Estado:** Fase 0 — Especificación y Arquitectura  

---

## 1. Contexto y Justificación
Durante la operación diaria es común que se presenten situaciones como:
- Salidas prematuras registradas por pruebas de debug o toques accidentales (ej. salida a las 15:09).
- Olvido de registrar la entrada al inicio de la jornada, lo que descoloca las marcas posteriores.
- Necesidad de corregir horarios de almuerzo o salida tras una interrupción.

Hasta ahora, la corrección requería invocar manualmente endpoints REST con herramientas como cURL o PowerShell. Esta funcionalidad incorpora un **Modo de Edición interactivo en el Bot de Telegram** protegido por `X-API-KEY` para permitir rectificaciones inmediatas y seguras desde el chat, y define el contrato de experiencia para su incorporación en la **App Móvil**.

---

## 2. Alcance (In-Scope)

### A. Implementación Inmediata: Bot de Telegram
1. **Comandos y Puntos de Entrada:**
   - Comando directo: `/editar` o `/editar_asistencia`.
   - Botón interactivo: Botón *"✏️ Modo Edición"* dentro del menú desplegado por `/horas`.
2. **Mecanismo de Autenticación y Privacidad:**
   - El bot solicita el ingreso de la `X-API-KEY`.
   - **Higiene estricta de privacidad:** El bot elimina inmediatamente el mensaje del usuario que contiene la clave (`bot.delete_message`) para no dejar credenciales expuestas en el historial de chat de Telegram.
   - Validación segura contra `is_valid_api_key(clave)` utilizando comparación criptográfica de tiempo constante (`hmac.compare_digest`).
   - Límite de 3 intentos fallidos antes de bloquear temporalmente el comando.
3. **Menú Interactivo de Edición (Inline Keyboard):**
   - 🔄 **"Limpiar Salida de Hoy"**: Acción inmediata de 1 click. Vacía `hora_salida` en SQLite (`NULL`), limpia la columna F en Google Sheets y deja la jornada en estado TRABAJANDO para poder marcar salida normalmente más tarde.
   - ✏️ **"Modificar Horarios de Hoy"**: Permite ingresar o rectificar: entrada, salida almuerzo, vuelta almuerzo y salida de la jornada en curso.
   - 📅 **"Rectificar Fecha Anterior"**: Ofrece la opción de seleccionar "Ayer" o escribir una fecha puntual (`YYYY-MM-DD`), guiando al usuario para ingresar los horarios correctos.
   - ❌ **"Cancelar"**: Cierra la sesión de edición de forma segura.
4. **Propagación en Vivo:**
   - Todo cambio exitoso se persiste en SQLite local (`LocalRepository.actualizar_jornada`) y se vuelca de inmediato con `SyncService.volcar_local_a_sheets(modulo="laboral", forzar=True)` a la planilla oficial (`SPREADSHEET_ID`), recalculando la fórmula en Columna G.

---

### B. Especificación para la App Móvil (Gamma Mobile)
1. **Interfaz de Usuario (UI/UX):**
   - En la tarjeta del reloj de asistencia (`EstadoJornadaCard`), se añade un botón de candado 🔒 *"Modo Edición"*.
2. **Autenticación en la App:**
   - Si la app ya tiene configurada y almacenada de forma segura la API Key (en `flutter_secure_storage`), puede desbloquear con biometría o PIN local.
   - De lo contrario, despliega un diálogo emergente solicitando la `X-API-KEY`.
3. **Capacidades en Pantalla Desbloqueada:**
   - Se habilitan selectores de hora (`TimePicker`) sobre los 4 tramos: Entrada, S. Almuerzo, V. Almuerzo y Salida.
   - Se provee un botón rápido *"Eliminar Salida"* (para reabrir la jornada).
   - Se habilita un selector de fecha en el calendario histórico para seleccionar días previos y corregirlos.
4. **Consumo de API:**
   - Las mutaciones se envían directamente al endpoint existente `PUT /api/v1/asistencia/jornadas/<fecha>` con cabecera `X-API-KEY`.

---

## 3. Fuera de Alcance (No-Scope)
- No aplica al módulo de asistencia de materias universitarias (cátedras).
- No aplica al módulo contable/financiero.
- No permite eliminación completa de la jornada (solo actualización y reseteo de marcas).

---

## 4. Matriz de Impacto e Invariantes (docs/SYSTEM_MAP.md)
- **Seguridad (`SYSTEM_MAP #S3`):** No se almacena la API Key en memoria compartida ni en logs. Los mensajes con claves se borran en tiempo real.
- **Aislamiento de Sheets (`SYSTEM_MAP #S1`):** La sincronización utiliza exclusivamente `SPREADSHEET_ID`.
- **Persistencia Local (`SYSTEM_MAP #P1`):** Mantiene la integridad referencial de `asistencia_laboral` en SQLite.
