# Research: Estrategia de Auto-eliminación de Botoneras y Mensajes en Telegram

## Decisiones Técnicas

### 1. Remoción de Botoneras vs Borrado Completo del Mensaje
- **Decisión:** Implementar dos estrategias diferenciadas según el tipo de interacción:
  1. `remover_teclado_inline(bot, chat_id, message_id)`: Utiliza `bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)` para neutralizar los botones sin perder el texto contextual del mensaje que originó la botonera.
  2. `eliminar_mensaje_seguro(bot, chat_id, message_id)`: Utiliza `bot.delete_message(chat_id, message_id)` encapsulado en un bloque seguro de captura de errores de Telegram API.
- **Por qué:** Si se borra por completo un mensaje que contenía opciones informativas, el chat pierde el hilo de la conversación. Remover únicamente el markup preserva el historial legible pero desactiva los botones para prevenir clics repetidos o desactualizados.
- **Alternativas descartadas:** Dejar los botones activos indefinidamente (causa clics erróneos y contaminación visual).

### 2. Tratamiento de Mensajes Transitorios de Carga ("⏳ Procesando...")
- **Decisión:** Implementar un helper contextual o patrón directo `with mensaje_cargando(...)` o `borrar_mensaje_cargando(bot, chat_id, loading_msg_id)`.
- **Por qué:** En comandos que tardan unos segundos (como OCR de facturas, consultas a Google Calendar o cálculo de deudas), el bot emite un mensaje de estado ("⏳ Procesando comprobante..."). Si no se elimina explícitamente tras la confirmación final, el chat acumula mensajes de espera inútiles.
- **Alternativas descartadas:** Editar siempre el mensaje de carga en lugar de enviar uno nuevo (rompe la visibilidad cuando el resultado final tiene un formato diferente, imágenes o PDFs adjuntos).

### 3. Tolerancia a Fallos y Manejo de Excepciones de Telegram API
- **Decisión:** Capturar y registrar silenciosamente excepciones específicas de Telegram:
  - Mensaje no encontrado (`message to delete not found`).
  - Mensaje no modificable / idéntico (`message is not modified`).
  - Mensaje mayor a 48 horas (`message can't be deleted`).
- **Por qué:** Las operaciones de limpieza nunca deben quebrar el flujo de negocio del usuario ni causar errores 500 en el webhook de producción de PythonAnywhere.
- **Alternativas descartadas:** Permitir propagación de excepciones en rutinas de UI efímera.

### 4. Modelo de Persistencia para Expiración (TTL)
- **Decisión:** Consolidar y sincronizar las lecturas/escrituras en `data/pending_deletions.json` utilizando un Lock de threading (`threading.Lock`) para evitar corrupción en accesos concurrentes de requests de webhook.
- **Por qué:** PythonAnywhere procesa peticiones HTTP concurrentes en workers WSGI; si dos llamadas intentan leer/escribir `pending_deletions.json` al mismo tiempo sin control, el JSON puede quedar corrupto (tamaño 0 bytes).
