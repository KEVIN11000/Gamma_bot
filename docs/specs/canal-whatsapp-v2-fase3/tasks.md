# CHECKLIST DE TAREAS: CANAL WHATSAPP Y WEBHOOKS DE RECEPCIÓN (V2.0.0 FASE 3)

**Feature:** `canal-whatsapp-v2-fase3`  
**Fecha:** 2 de Noviembre de 2026  
**Regla de Ejecución:** Tareas atómicas, secuenciales e independientes. No se inicia una nueva tarea hasta que los tests de la actual pasen en la terminal.

---

## TAREAS DE CONSTRUCCIÓN

- [x] **Tarea 1: Módulo de Utilidad para Saneamiento y Normalización Telefónica E.164 (`src/utils/phone_utils.py`)**
  - **Descripción:** Implementar funciones para limpiar, formatear y normalizar identificadores de números celulares hacia el estándar E.164 (eliminación de espacios, guiones, ceros iniciales locales y sufijos JID como `@s.whatsapp.net`).
  - **Criterio de Aceptación:** Test unitario en `tests/test_phone_utils.py` validando números paraguayos (+595 981...), números locales (0981...), identificadores JID y números internacionales.

- [x] **Tarea 2: Adaptador Saliente de WhatsApp (`src/adapters/notifications/whatsapp_adapter.py`)**
  - **Descripción:** Implementar `WhatsAppNotificationAdapter` cumpliendo la interfaz `INotificationPort`. Debe realizar peticiones HTTP hacia la pasarela de WhatsApp (Evolution API / Meta Cloud) para el envío de mensajes de texto y documentos PDF en base64, con timeout configurable y captura controlada de errores.
  - **Criterio de Aceptación:** Test unitario en `tests/test_whatsapp_adapter.py` con mocking de peticiones HTTP (`requests` / `urllib`), validando cabeceras de autorización, URLs construidas, codificación de adjuntos y manejo de errores con `raise_on_error`.

- [x] **Tarea 3: DTOs Pydantic v2 para Eventos de Webhook de WhatsApp (`src/api/schemas.py`)**
  - **Descripción:** Definir los modelos de validación `WhatsAppMessageData` y `WhatsAppWebhookEvent` para la ingesta tipada y validación de eventos entrantes de la API de WhatsApp.
  - **Criterio de Aceptación:** Tests unitarios en `tests/test_whatsapp_webhooks.py` validando serialización/deserialización de eventos válidos y rechazo con error 422 ante payloads mal formados.

- [x] **Tarea 4: Endpoint REST Receptor de Webhooks (`POST /api/v1/webhooks/whatsapp`)**
  - **Descripción:** Crear el submódulo de rutas `src/api/v1/routes_webhooks.py`, integrarlo a `v1_bp`, validar cabecera secreta (`X-Webhook-Secret`), ignorar mensajes de eco (`from_me = True`) y encolar el trabajo asíncrono en `cola.db` con `channel = "whatsapp"`.
  - **Criterio de Aceptación:** Test de endpoint en `tests/test_whatsapp_webhooks.py` con cliente de pruebas de Flask (`client.post`), verificando respuesta HTTP 200, autorización correcta, rechazo HTTP 401 si el secret es inválido y presencia del trabajo en la cola.

- [x] **Tarea 5: Integración del Canal WhatsApp en el Worker y Despachador Global**
  - **Descripción:** Registrar el adaptador `whatsapp` en el flujo de inicialización del `NotificationDispatcher` cuando existan variables de entorno configuradas (`WHATSAPP_API_URL`), permitiendo el procesamiento nativo de tareas encoladas para dicho canal.
  - **Criterio de Aceptación:** Test de integración en `tests/test_worker_multichannel.py` verificando el ciclo completo de encolado, procesamiento y despacho a través de `WhatsAppNotificationAdapter`.

- [x] **Tarea 6: Verificación Integral de Suite de Calidad y Cierre de Fase 3**
  - **Descripción:** Ejecución completa de suites de linters (`black --check`, `flake8`, `mypy`) y suite total de pruebas `pytest` (alcanzando 100% de tests aprobados sin ninguna regresión sobre los 309 tests existentes).
  - **Criterio de Aceptación:** `uv run pytest` pasa al 100% con los nuevos tests incluidos, `mypy` 0 errores, `flake8` 0 errores, `black` 0 desvíos.
