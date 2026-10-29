# Data Model: Gestión de Mensajes Efímeros y Teclados

## Entidades y Estructuras

### 1. `PendingDeletion` (Esquema en disco `data/pending_deletions.json`)

Representa un mensaje agendado para eliminación o expiración.

```json
{
  "<chat_id>_<message_id>": {
    "chat_id": 12345678,
    "message_id": 9876,
    "expire_at": 1730198400.0,
    "action": "delete" // "delete" | "clear_markup"
  }
}
```

*Compatibilidad retroactiva:*
Si la clave tiene como valor un número simple `{"123_456": 1730198400.0}`, el motor lo interpreta automáticamente como acción `"delete"` con `chat_id=123` y `message_id=456`.

---

### 2. `TransientMessage` (En memoria / Context Manager)

Estructura ligera de control para mensajes de carga intermedios:

- `chat_id: int | str`: Identificador del chat.
- `message_id: int`: Identificador del mensaje de espera ("⏳ Procesando...").
- `created_at: float`: Timestamp de creación.
