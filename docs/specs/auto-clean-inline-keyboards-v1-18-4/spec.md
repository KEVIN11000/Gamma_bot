# Feature Specification: Auto-eliminación y expiración de botoneras y mensajes en Telegram

**Feature Branch**: `feature/auto-clean-inline-keyboards-v1-18-4`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Auto-eliminación de botoneras interactivas, mensajes de estado de carga y expiración en Telegram (Ticket TG-fc5352bf)"

## User Scenarios & Testing

### User Story 1 - Limpieza inmediata de teclados y mensajes de carga al responder interacción (Priority: P1)

Como usuario de Gamma Bot en Telegram, al interactuar con un menú interactivo (`InlineKeyboardMarkup`) o cuando se confirma una acción (por ejemplo marcar asistencia, confirmar gasto o borrar aviso), quiero que la botonera interactiva quede reemplazada o removida y que los mensajes transitorios de estado ("Procesando...", "Cargando...") se eliminen, para mantener limpio el historial del chat sin contaminación visual ni duplicidad de clics accidentales.

**Why this priority**: Evita la polución visual del chat, previene que el usuario presione botones viejos/obsoletos que disparen errores o respuestas duplicadas en handlers, y preserva la confirmación final de registro.

**Independent Test**: Interactuar con un flujo de callback (ej. selección en `/marcar` o `/fijos`) y verificar que el markup inline se remueva (`edit_message_reply_markup(reply_markup=None)`) o el mensaje efímero se borre, mientras que el mensaje final con el comprobante/confirmación persiste.

**Acceptance Scenarios**:
1. **Given** un mensaje con botonera interactiva (`InlineKeyboardMarkup`), **When** el usuario presiona un botón de acción definitiva, **Then** el teclado inline queda eliminado o deshabilitado inmediatamente y se muestra la respuesta final.
2. **Given** un mensaje temporal de espera o carga ("⏳ Procesando...", "⏳ Generando reporte..."), **When** el proceso concluye con éxito o error, **Then** el mensaje temporal es eliminado o editado con el resultado final sin dejar mensajes huérfanos.

---

### User Story 2 - Expiración automática y segura de menús interactivos no respondidos (Priority: P2)

Como usuario, si abro un menú interactivo (ej. menú principal `/start`, listado de deudas o selector de reportes) y no interactúo con él durante un tiempo determinado (TTL configurable), quiero que los botones o el mensaje expiren de forma controlada y resiliente, sin provocar excepciones en el servidor si el usuario ya lo borró previamente.

**Why this priority**: En conversaciones donde el usuario no presiona ninguna opción y continúa escribiendo otros comandos, los menús abandonados quedan flotando y pueden causar clics no sincronizados horas después.

**Independent Test**: Enviar un menú con expiración configurada y verificar que, cumplido el tiempo o al ejecutarse `limpiar_menus_expirados()`, el mensaje o la botonera sea removida del chat y desregistrada de la cola de pendientes sin fallar en caso de `MessageToDeleteNotFound`.

**Acceptance Scenarios**:
1. **Given** un menú enviado con TTL, **When** expira el tiempo establecido, **Then** el menú es limpiado y se descarta de la cola de pendientes en disco.
2. **Given** que un mensaje con expiración ya fue borrado manualmente por el usuario en Telegram, **When** se ejecuta la rutina de limpieza, **Then** el error es capturado silenciosamente y el registro huérfano se purga de la lista persistente.

---

### User Story 3 - Preservación estricta de comprobantes y textos informativos útiles (Priority: P3)

Como usuario contable y administrativo, quiero que los mensajes de confirmación de transacciones (tickets de gasto, marcaciones horarias registradas, resúmenes contables y reportes PDF) NUNCA sean eliminados automáticamente, para garantizar auditoría histórica en el chat personal.

**Why this priority**: Cumple con la observación del usuario en `TG-fc5352bf`: *"cosas como los textos de marcación o registro confirmado son útiles conservar"*.

**Independent Test**: Ejecutar un ciclo completo de marcación laboral o registro de gasto y verificar que el mensaje final de éxito permanezca indefinidamente en el chat sin asociarse a colas de expiración efímeras.

**Acceptance Scenarios**:
1. **Given** una marcación laboral registrada exitosamente, **When** finaliza la operación, **Then** el texto con hora, fecha y fila asignada permanece en el chat.

---

### Edge Cases

- **Mensaje ya eliminado por el usuario (`MessageToDeleteNotFound` / `message can't be deleted`)**: La función de limpieza debe capturar la excepción de Telebot/Telegram API sin propagar error ni interrumpir hilos de ejecución.
- **Mensaje demasiado viejo (>48 horas)**: Telegram prohíbe el borrado de ciertos mensajes antiguos mediante bot en chats privados; el sistema debe atrapar la excepción y simplemente descartar la clave del almacenamiento local para no reintentar eternamente.
- **Concurrencia en `pending_deletions.json`**: Múltiples timers o peticiones concurrentes escribiendo en el archivo de mensajes pendientes deben manejar serialización segura o tolerancia a accesos simultáneos.
- **Botón presionado dos veces rápidamente**: La eliminación o limpieza de la botonera debe ocurrir atómicamente o verificar estado antes de volver a ejecutar la lógica de negocio.

---

## Requirements

### Functional Requirements

- **FR-001**: El sistema DEBE proveer un helper unificado para remover botoneras inline (`InlineKeyboardMarkup`) de mensajes existentes (`edit_message_reply_markup(chat_id, message_id, reply_markup=None)`) de forma segura ante excepciones de Telegram.
- **FR-002**: El sistema DEBE proveer un mecanismo seguro para rastrear y eliminar mensajes transitorios ("cargando" / "procesando") una vez completada la acción correspondiente.
- **FR-003**: El helper `limpiar_menus_expirados` DEBE ser robusto ante caídas de red, mensajes inexistentes o limitaciones de API de Telegram (mensajes > 48h), purgando las entradas sin lanzar excepciones no controladas.
- **FR-004**: Los mensajes de confirmación permanente (comprobantes de gastos, marcaciones, balances y reportes) DEBEN quedar expresamente excluidos de borrado automático.
- **FR-005**: La persistencia de mensajes pendientes en `pending_deletions.json` DEBE mantener integridad de datos ante reinicios o recargas WSGI en PythonAnywhere.

### Key Entities

- **PendingDeletion**: Registro persistente compuesto por `chat_id`, `message_id`, `expire_timestamp` y `deletion_type` (ej. `delete_message` vs `clear_markup`).
- **TransientContext**: Contexto efímero durante la ejecución de comandos para retener el `message_id` del mensaje de carga ("⏳ Procesando...") hasta sustituirlo o borrarlo tras emitir el resultado final.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% de los callbacks interactivos de menú principal y flujos transitorios limpian su botonera o eliminan el mensaje temporal al finalizar la acción.
- **SC-002**: 0 mensajes huérfanos de "⏳ Procesando..." permanecen en el chat tras la confirmación exitosa o error de una operación.
- **SC-003**: 100% de los comprobantes contables y marcaciones de asistencia se mantienen en el historial del chat sin borrarse.
- **SC-004**: 0 excepciones no controladas en logs por fallos de eliminación en Telegram API (ej. mensajes ya borrados o expirados).

---

## Assumptions

- Telegram Bot API permite la edición y borrado de mensajes enviados por el propio bot en chats privados dentro de la ventana estándar de 48 horas.
- La ejecución en PythonAnywhere opera mediante Webhook WSGI, por lo que las rutinas de expiración diferidas se apoyan tanto en timers en memoria como en la comprobación periódica en hooks de ciclo de vida (`limpiar_menus_expirados`).
- No se requiere una base de datos relacional para expiración de menús; un archivo JSON o almacenamiento ligero en `data/pending_deletions.json` es suficiente para el volumen del bot.
