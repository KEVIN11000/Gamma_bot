# PLAN DE ARQUITECTURA TÉCNICA: CANAL WHATSAPP Y WEBHOOKS DE RECEPCIÓN (V2.0.0 FASE 3)

**Feature:** `canal-whatsapp-v2-fase3`  
**Fecha:** 2 de Noviembre de 2026  
**Fase:** Fase 0 — Especificación y Arquitectura  

---

## 1. Diagrama de Arquitectura y Flujo

```mermaid
flowchart TD
    subgraph WhatsApp Gateway [Gateway Externo (Evolution / Meta API)]
        WA_In[Mensaje Entrante]
        WA_Out[Envío de Mensaje/Doc]
    end

    subgraph API REST [Flask API v1]
        WebhookRoute["POST /api/v1/webhooks/whatsapp"]
        AuthCheck["Validación X-Webhook-Secret"]
        DTOVal["Validación Pydantic WhatsAppWebhookEvent"]
    end

    subgraph Asynchronous Queue [Cola de Fondo (cola.db)]
        QueueDB[(cola.db: recipient_id, channel='whatsapp')]
        WorkerProcess["Worker / procesar_trabajos_pendientes"]
    end

    subgraph Adapters & Dispatcher [Despacho Multi-Canal]
        Dispatcher["NotificationDispatcher"]
        WAAdapter["WhatsAppNotificationAdapter : INotificationPort"]
    end

    WA_In --> WebhookRoute
    WebhookRoute --> AuthCheck --> DTOVal --> QueueDB
    WorkerProcess --> Dispatcher --> WAAdapter --> WA_Out
```

---

## 2. Contratos de Datos y Esquemas Pydantic v2

### 2.1. DTO de Eventos de Webhook (`src/api/schemas.py` o módulo dedicado)
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class WhatsAppMessageData(BaseModel):
    remote_jid: str = Field(..., description="ID del chat o número E.164")
    from_me: bool = Field(False, description="True si fue enviado por la propia instancia")
    push_name: Optional[str] = Field(None, description="Nombre visible del usuario")
    text: Optional[str] = Field(None, description="Cuerpo del mensaje de texto")
    message_type: str = Field("conversation", description="conversation, extendedTextMessage, documentMessage")
    raw_payload: Dict[str, Any] = Field(default_factory=dict)

class WhatsAppWebhookEvent(BaseModel):
    event: str = Field(..., description="Tipo de evento: messages.upsert, send.message, connection.update")
    instance: str = Field(..., description="Nombre de la instancia que emitió el evento")
    data: WhatsAppMessageData
```

### 2.2. Utilidad de Saneamiento Telefónico (`src/utils/phone_utils.py`)
```python
def normalize_phone_number(raw_phone: str, default_country_code: str = "595") -> str:
    """Sanea y normaliza cadenas a formato numérico E.164 canónico.
    
    Ejemplos:
        '0981 123 456' -> '595981123456'
        '+595 981-123456' -> '595981123456'
        '595981123456@s.whatsapp.net' -> '595981123456'
    """
```

---

## 3. Adaptador de WhatsApp (`src/adapters/notifications/whatsapp_adapter.py`)

### 3.1. Especificación del Adaptador
- Implementa `INotificationPort`.
- Atributos:
  - `api_url: str` (ej. `http://gateway.local:8080` o URL en la nube).
  - `api_key: str` (token de autenticación por cabecera `apikey` o `Authorization: Bearer`).
  - `instance_name: str` (nombre de instancia de Evolution API).
  - `timeout: float = 10.0` (protección contra bloqueos).
- Métodos:
  - `send_message(recipient_id: str, message: str, parse_mode: Optional[str] = None, **kwargs) -> bool`
    Envía petición `POST /message/sendText/{instance}` con payload `{"number": recipient_id, "text": message}`.
  - `send_document(recipient_id: str, document_path: str, caption: str = "", visible_file_name: Optional[str] = None, **kwargs) -> bool`
    Codifica el archivo a base64 o multipart y emite `POST /message/sendMedia/{instance}` con mimetype `application/pdf`.

---

## 4. Rutas de Webhook (`src/api/v1/routes_webhooks.py`)

- `POST /api/v1/webhooks/whatsapp`:
  1. Verifica cabecera de autenticación (`X-Webhook-Secret` coincidente con `WHATSAPP_WEBHOOK_SECRET` o rechaza con HTTP 401).
  2. Parsea y valida el cuerpo JSON mediante `WhatsAppWebhookEvent`.
  3. Si el mensaje es saliente (`from_me = True`), responde HTTP 200 inmediatamente (ignora eco).
  4. Si contiene texto, encola el comando/mensaje mediante `enqueue(recipient_id=data.remote_jid, operacion="procesar_mensaje_whatsapp", payload={...}, channel="whatsapp")`.
  5. Responde HTTP 200 con `{"status": "enqueued"}` en < 25ms para evitar timeouts en el gateway.

---

## 5. Estrategia de Testing

1. `tests/test_phone_utils.py`: Casos de prueba exhaustivos de saneamiento telefónico para Paraguay y números internacionales.
2. `tests/test_whatsapp_adapter.py`: Mocking HTTP completo de Evolution API para envíos de texto, documentos PDF y manejo de caídas de red (HTTP 500/timeout).
3. `tests/test_whatsapp_webhooks.py`: Tests de integración REST sobre el endpoint `/api/v1/webhooks/whatsapp` validando autorización, rechazo de payloads inválidos, filtrado de mensajes propios y encolamiento asíncrono.
