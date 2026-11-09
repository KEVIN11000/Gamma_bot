# Plan de Arquitectura y Diseño Técnico: Modo de Edición de Asistencia

**Feature:** `modo-edicion-asistencia`  
**Fecha:** 2026-11-05  
**Estado:** Fase 0 — Especificación y Arquitectura  

---

## 1. Módulos y Componentes Involucrados

```
[Usuario Telegram] 
        │
        ▼  /editar o botón en /horas
[src/com/handlers/asistencia.py]
        │
        ├─ 1. Solicitar clave
        ├─ 2. Interceptar mensaje -> bot.delete_message (Higiene)
        ├─ 3. is_valid_api_key(clave) (src/api/security.py)
        │       └─ Si falla: reintento o aborto
        │       └─ Si acierta: mostrar menú inline
        ▼
[Menú Inline de Edición]
        ├─ "edit_asist:limpiar_salida_hoy"
        ├─ "edit_asist:editar_hoy"
        ├─ "edit_asist:editar_ayer"
        ├─ "edit_asist:editar_fecha"
        └─ "edit_asist:cancelar"
        │
        ▼
[src/services/asistencia_service.py / edicion_asistencia_service.py]
        │
        ├─ Actualizar SQLite vía LocalRepository.actualizar_jornada
        ├─ Recalcular horas_decimal vía AgenteAutonomoHoras.calcular_horas_jornada
        └─ SyncService(spreadsheet_id=SPREADSHEET_ID).volcar_local_a_sheets(modulo="laboral", forzar=True)
        │
        ▼
[Confirmación al Usuario en Telegram con resumen actualizado]
```

---

## 2. Flujo Detallado de Conversación y Callbacks

### 2.1. Desbloqueo por X-API-KEY
1. Al invocar `/editar` o pulsar *"✏️ Modo Edición"*, el bot responde:
   `"🔒 <b>Modo Edición de Asistencia</b>\n\nIngresa tu <code>X-API-KEY</code> para autenticarte.\n<i>(Tu mensaje será eliminado inmediatamente del chat por privacidad).</i>"`
2. Se registra un step handler (`bot.register_next_step_handler`).
3. Al recibir la respuesta:
   - Se ejecuta inmediatamente `bot.delete_message(chat_id, message.message_id)`.
   - Se evalúa `is_valid_api_key(texto.strip())`.
   - Si es inválida: envía mensaje de advertencia y cancela o permite 1 reintento.
   - Si es válida: envía el mensaje de menú con teclado inline.

### 2.2. Acción 1: "Limpiar Salida de Hoy"
- Callback data: `edit_asist:limpiar_salida_hoy`.
- Lógica:
  1. Obtiene la jornada de hoy en SQLite (`repo.obtener_jornada_por_fecha(fecha_hoy)`).
  2. Si no hay jornada o no tiene salida: responde `"ℹ️ Hoy no tienes ninguna salida registrada."`
  3. Si tiene salida: actualiza en SQLite `hora_salida = None`, `horas_decimal = 0.0`, `sincronizado_sheets = 0`.
  4. Dispara `SyncService.volcar_local_a_sheets(mes=hoy.month, anio=hoy.year, modulo="laboral", forzar=True)`.
  5. Edita el mensaje mostrando:
     `"✅ <b>Salida de hoy eliminada exitosamente.</b>\nLa celda en Google Sheets fue limpiada y la jornada quedó abierta. Podrás marcar normalmente al retirarte."`

### 2.3. Acción 2: "Rectificar Ayer (04/11/2026)"
- Callback data: `edit_asist:editar_ayer`.
- Lógica:
  1. Pide al usuario enviar los horarios en formato simple:
     `"Envía los horarios separados por coma o espacio:\n<code>ENTRADA, SALIDA_ALMUERZO, VUELTA_ALMUERZO, SALIDA</code>\n\n<i>Ejemplo: 08:45, 12:00, 13:00, 17:06</i>"`
  2. Valida cada tramo con regex `HH:MM`.
  3. Invoca la lógica de rectificación con recálculo automático de `horas_decimal` y volcado forzado a Sheets.
  4. Responde con el cuadro resumen confirmado.

### 2.4. Acción 3: "Rectificar Otra Fecha"
- Callback data: `edit_asist:editar_fecha`.
- Pide fecha `YYYY-MM-DD` y luego solicita los horarios con el mismo validador.

---

## 3. Plan de Integración con la App Móvil
- El documento `spec.md` contendrá la arquitectura de componentes y contrato de API (`PUT /api/v1/asistencia/jornadas/<fecha>`) para ser implementado en el frontend Flutter/React Native de Gamma Mobile en su respectiva iteración móvil.
