# ESPECIFICACIÓN TÉCNICA: CANAL WHATSAPP Y WEBHOOKS DE RECEPCIÓN (V2.0.0 FASE 3)

**Feature:** `canal-whatsapp-v2-fase3`  
**Fecha:** 2 de Noviembre de 2026  
**Fase:** Fase 0 — Especificación y Arquitectura  
**Estado:** Propuesta en Revisión  

---

## 1. Contexto y Objetivos

Con la culminación de la Fase 2, el subsistema de tareas en background (`src/app_queue/worker.py`) quedó desacoplado y gobernado por [`INotificationPort`](file:///e:/PG/vcp-s/Gamma_bot/src/ports/notification_port.py) y [`NotificationDispatcher`](file:///e:/PG/vcp-s/Gamma_bot/src/services/notification_dispatcher.py).

El objetivo de la **Fase 3** es habilitar el canal de mensajería **WhatsApp** como canal de primer nivel para Gamma Bot:
1. Implementar el adaptador saliente `WhatsAppNotificationAdapter` bajo el puerto canónico `INotificationPort` (compatible con Evolution API / Meta Cloud API).
2. Normalizar identificadores de destinatarios en formato internacional canónico E.164 (ej. `+595981XXXXXX`).
3. Diseñar y exponer el endpoint receptor de webhooks `POST /api/v1/webhooks/whatsapp` para la ingesta asíncrona de eventos y mensajes entrantes.
4. Conectar de forma nativa la resolución del canal `"whatsapp"` en el `NotificationDispatcher`.

---

## 2. Alcance (In-Scope)

1. **Adaptador Saliente `WhatsAppNotificationAdapter` (`src/adapters/notifications/whatsapp_adapter.py`):**
   - Implementación de `INotificationPort`.
   - Envío de mensajes de texto mediante peticiones HTTP autenticadas (POST JSON).
   - Envío de documentos (PDFs) en base64 o multipart/media endpoint según el contrato de la pasarela.
   - Parámetros de entorno configurables: `WHATSAPP_API_URL`, `WHATSAPP_API_KEY`, `WHATSAPP_INSTANCE_NAME`.
   - Reintentos exponenciales y manejo de fallas de red con `raise_on_error`.

2. **Normalizador de Destinatarios Telefónicos (`src/utils/phone_utils.py`):**
   - Validación y saneamiento de números a formato canónico internacional (eliminación de guiones, espacios y prefijos locales incorrectos).
   - Soporte para prefijo estándar paraguayo (+595) y compatibilidad con formatos de chat ID (`595981...@s.whatsapp.net`).

3. **Endpoint de Recepción Webhook (`POST /api/v1/webhooks/whatsapp`):**
   - Integrado en `src/api/v1/routes_webhooks.py` y registrado en `v1_bp`.
   - Validación de token de autenticación / webhook secret (`WHATSAPP_WEBHOOK_SECRET` o header `X-Webhook-Secret`).
   - DTOs de validación con Pydantic v2 para la ingesta de mensajes y estados de entrega.
   - Encolamiento agnóstico del mensaje entrante en `cola.db` (`channel = 'whatsapp'`) para procesamiento asíncrono sin bloquear el worker WSGI de PythonAnywhere.

4. **Registro en el Despachador:**
   - Incorporación automática de la fábrica o registro del canal `"whatsapp"` en el contenedor de servicios y worker.

---

## 3. Fuera de Alcance (No-Scope)

- **Cobros directos en chat mediante WhatsApp Pay:** Excluido por falta de disponibilidad regional.
- **Reconocimiento y procesamiento de notas de voz en tiempo real:** Excluido para esta iteración.
- **Modificación de reglas contables o modelos de jornada laboral existentes.**

---

## 4. Requisitos de Calidad y Resiliencia

- **Aislamiento de Producción:** Prohibido emitir peticiones HTTP reales a servidores en vivo durante tests unitarios (uso estricto de `responses` / `unittest.mock`).
- **Seguridad de Secretos:** Configuración exclusivamente vía variables de entorno con fallbacks seguros en modo desarrollo/testing.
- **Cero Regresiones:** Los 309 tests existentes deben mantenerse en verde al 100%.
