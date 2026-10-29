# Quickstart: Validación de Auto-eliminación y Teclados

## Escenarios de Prueba Rápida

### Escenario 1: Remoción de markup tras confirmación de callback
1. Ejecutar mock de bot de Telegram.
2. Simular un mensaje con `InlineKeyboardMarkup`.
3. Invocar `remover_teclado_inline(mock_bot, chat_id, message_id)`.
4. **Resultado esperado:** `mock_bot.edit_message_reply_markup` invocado con `reply_markup=None`. Retorna `True`.

### Escenario 2: Mensaje ya eliminado (Tolerancia a fallos)
1. Simular `mock_bot.delete_message` lanzando excepción `ApiTelegramException: message to delete not found`.
2. Invocar `eliminar_mensaje_seguro(mock_bot, chat_id, message_id)`.
3. **Resultado esperado:** La excepción es amortiguada; la función retorna `True` (o limpia la entrada) sin romper la ejecución.

### Escenario 3: Purgado de cola en `limpiar_menus_expirados`
1. Poblar un archivo temporal con dos entradas vencidas y una entrada futura.
2. Invocar `limpiar_menus_expirados(mock_bot)`.
3. **Resultado esperado:** Se eliminan las dos entradas vencidas y sólo permanece la entrada futura en el archivo.
