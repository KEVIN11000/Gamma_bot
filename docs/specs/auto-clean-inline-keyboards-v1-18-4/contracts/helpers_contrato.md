# Contratos de Interfaz: Módulo de Limpieza de Mensajes y Teclados

## Funciones Core (`src/com/core/utils.py`)

### 1. `eliminar_mensaje_seguro(bot: Any, chat_id: Any, message_id: Any) -> bool`
- **Descripción:** Intenta eliminar un mensaje en Telegram capturando excepciones conocidas (mensaje inexistente, ya borrado o mayor a 48h).
- **Entrada:**
  - `bot`: Instancia de TeleBot.
  - `chat_id`: int o str.
  - `message_id`: int o str.
- **Salida:** `True` si se borró con éxito o si ya no existe; `False` en caso de error no recuperable.

---

### 2. `remover_teclado_inline(bot: Any, chat_id: Any, message_id: Any) -> bool`
- **Descripción:** Neutraliza la botonera de un mensaje existente enviando `reply_markup=None`.
- **Entrada:**
  - `bot`: Instancia de TeleBot.
  - `chat_id`: int o str.
  - `message_id`: int o str.
- **Salida:** `True` si se actualizó el markup o si el mensaje ya no tiene teclado; `False` ante otros fallos.

---

### 3. `limpiar_menus_expirados(bot: Any) -> int`
- **Descripción:** Recorre `pending_deletions.json`, ejecuta las acciones vencidas (borrado o remoción de markup) y purga los registros expirados o fallidos.
- **Entrada:**
  - `bot`: Instancia de TeleBot.
- **Salida:** Cantidad de elementos eliminados/procesados.
