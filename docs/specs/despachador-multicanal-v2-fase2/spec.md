# ESPECIFICACIÓN TÉCNICA: DESPACHADOR MULTI-CANAL Y COLA AGNÓSTICA (V2.0.0 FASE 2)

**Feature:** `despachador-multicanal-v2-fase2`  
**Fecha:** 2 de Noviembre de 2026  
**Fase:** Fase 0 — Especificación y Arquitectura  
**Estado:** Propuesta en Revisión  

---

## 1. Contexto y Objetivos

En la Fase 1 de la versión 2.0.0 se consolidó la persistencia primaria local (`gamma_local.db`), la unificación contable y la modularización de la API REST. Sin embargo, el subsistema de encolamiento y tareas en segundo plano (`src/app_queue/worker.py`) permanece acoplado directamente al SDK de Telegram (`telebot`):
- Las llamadas a `enqueue(chat_id: int, ...)` asumen un identificador numérico entero exclusivo de Telegram.
- La tabla SQLite `queue` en `cola.db` define la columna `chat_id INTEGER NOT NULL`.
- La función despachadora `despachar_trabajo(bot, operacion, payload, chat_id)` invoca de forma directa métodos de Telegram (`bot.send_message`, `bot.send_document`), imposibilitando el despacho de avisos a otros canales como WhatsApp o la app Gamma Mobile.

El objetivo de la **Fase 2** es desacoplar el procesamiento asíncrono y el envío de notificaciones mediante una arquitectura de puertos y adaptadores (*Hexagonal / Clean Architecture*), permitiendo:
1. Unificar el envío de notificaciones a través de la interfaz `INotificationPort`.
2. Implementar `TelegramNotificationAdapter` preservando la operatividad actual de Telegram.
3. Migrar de forma transparente y retrocompatible la base de datos `cola.db` para admitir `recipient_id TEXT` y `channel TEXT`.
4. Disponer de un despachador extensible (`NotificationDispatcher`) que permita registrar futuros adaptadores (ej. WhatsApp / Push en Fase 3) sin tocar la lógica de negocio ni el worker.

---

## 2. Alcance (In-Scope)

1. **Abstracción de Notificaciones (`INotificationPort`):**
   - Definición de interfaz tipada para envío de mensajes de texto estructurados y documentos adjuntos (PDFs).
   - Manejo de metadatos de canal (modo de parseo, nombres de archivo visible, flags silenciosos).

2. **Adaptador Canónico de Telegram (`TelegramNotificationAdapter`):**
   - Envoltorio desacoplado que implementa `INotificationPort` sobre el cliente `telebot.TeleBot`.
   - Traducción de firmas de métodos canónicos a llamadas de Telegram (`send_message`, `send_document`).

3. **Adaptador de Pruebas (`MockNotificationAdapter`):**
   - Implementación en memoria para tests unitarios rápidos y deterministas sin dependencias de red ni mocks complejos.

4. **Despachador Centralizado (`NotificationDispatcher`):**
   - Registro dinámico de adaptadores indexados por canal (`telegram`, `whatsapp`, `mobile`, `mock`).
   - Resolución automática de canal por defecto (`telegram`) ante peticiones no especificadas.
   - Enrutamiento seguro y manejo centralizado de excepciones de entrega.

5. **Evolución Retrocompatible de `cola.db`:**
   - Migración automática no destructiva en `init_db()`: incorporación de columnas `recipient_id TEXT` y `channel TEXT DEFAULT 'telegram'`.
   - Poblado retrocompatible automático: si `recipient_id` es nulo, inicializar con el valor de `chat_id`.

6. **Desacoplamiento de `src/app_queue/worker.py`:**
   - `enqueue()` soporta tanto la firma histórica `(chat_id: int, ...)` como la nueva firma agnóstica `(recipient_id: str | int, ..., channel: str = "telegram")`.
   - `procesar_trabajos_pendientes()` admite la inyección del bot tradicional de Telegram (envolviéndolo automáticamente) o de una instancia de `NotificationDispatcher`.
   - `despachar_trabajo()` interactúa exclusivamente a través de `INotificationPort`, eliminando llamadas a métodos propietarios de SDKs.

---

## 3. Fuera de Alcance (No-Scope)

- **Integración viva de Evolution API / WhatsApp Cloud API:** Corresponde a la Fase 3 una vez completado el desacoplamiento de la infraestructura.
- **Implementación de Webhooks o Workers de Background para WhatsApp:** Excluido de Fase 2.
- **Desarrollo de UI / Android Compose en Gamma Mobile:** Corresponde a Fase 3.
- **Alteración de modelos de dominio contable o laboral:** La lógica en `src/logic/` se mantiene intacta.

---

## 4. Requisitos de Retrocompatibilidad

- **Cero Breaking Changes:** Ninguna invocación actual de `enqueue(...)` en los manejadores de Telegram (`asistencia.py`, `avisos.py`, `deudas.py`, `finanzas.py`) ni en `flask_app.py` o `run_bot.py` debe fallar ni requerir refactorización obligatoria inmediata.
- **Persistencia Existente:** Si existe un archivo `cola.db` con trabajos pendientes o completados, la migración en caliente (`ALTER TABLE`) debe preservar intactos los registros existentes.
- **Suite de Pruebas:** Los 282 tests existentes deben seguir pasando al 100% sin regresiones.
