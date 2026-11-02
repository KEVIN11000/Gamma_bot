# CHECKLIST DE TAREAS: DESPACHADOR MULTI-CANAL Y COLA AGNÓSTICA (V2.0.0 FASE 2)

**Feature:** `despachador-multicanal-v2-fase2`  
**Fecha:** 2 de Noviembre de 2026  
**Regla de Ejecución:** Tareas atómicas, secuenciales e independientes. No se inicia una nueva tarea hasta que los tests de la actual pasen en la terminal.

---

## TAREAS DE CONSTRUCCIÓN

- [x] **Tarea 1: Definición del Puerto de Notificaciones y Adaptador Mock (`src/ports/` y `src/adapters/`)**
  - **Descripción:** Crear la interfaz canónica `INotificationPort` con los métodos abstractos `send_message` y `send_document`. Implementar `MockNotificationAdapter` para pruebas unitarias rápidas con trazabilidad en memoria de mensajes y documentos enviados.
  - **Criterio de Aceptación:** Test unitario en `tests/test_notification_ports.py` verificando la firma del protocolo, la captura de mensajes y documentos en el mock, y el paso limpio de tipos en `mypy`.

- [x] **Tarea 2: Adaptador de Telegram Desacoplado (`src/adapters/notifications/telegram_adapter.py`)**
  - **Descripción:** Implementar `TelegramNotificationAdapter` que envuelve una instancia de `bot` (tipo `telebot.TeleBot` o similar). Debe manejar la conversión segura de `recipient_id` a entero, llamadas a `bot.send_message`, apertura y envío seguro de archivos para `bot.send_document`, y captura controlada de errores de red o del SDK.
  - **Criterio de Aceptación:** Tests unitarios en `tests/test_notification_ports.py` con mock de `telebot` verificando el reenvío de mensajes con parse mode y el envío de PDFs con descriptor de archivo cerrado tras la llamada.

- [x] **Tarea 3: Despachador de Canales (`src/services/notification_dispatcher.py`)**
  - **Descripción:** Crear la clase `NotificationDispatcher` que gestiona el registro de adaptadores por canal (`register_adapter(channel, adapter)`), la resolución por canal con fallback seguro al canal por defecto (`telegram`), y el envío a través de los adaptadores registrados.
  - **Criterio de Aceptación:** Test unitario en `tests/test_notification_dispatcher.py` validando registro múltiple, despacho al canal indicado, lanzamiento de error controlado si el canal no existe, y comportamiento por defecto.

- [x] **Tarea 4: Migración no Destructiva de la Base de Datos de Cola (`cola.db`)**
  - **Descripción:** Actualizar la función `init_db()` en `src/app_queue/worker.py` para detectar esquemas anteriores e incorporar de forma segura las columnas `recipient_id TEXT` y `channel TEXT NOT NULL DEFAULT 'telegram'`, migrando registros previos de `chat_id` hacia `recipient_id`.
  - **Criterio de Aceptación:** Test unitario en `tests/test_queue_migration.py` que cree una base de datos SQLite temporal con el esquema antiguo v1, inserte registros de prueba, ejecute `init_db()` y confirme que las nuevas columnas existen y los datos previos fueron migrados correctamente sin pérdida.

- [x] **Tarea 5: Refactorización Agnóstica del Worker (`src/app_queue/worker.py`)**
  - **Descripción:** Modificar `enqueue`, `despachar_trabajo` y `procesar_trabajos_pendientes` para operar con `INotificationPort` y `recipient_id` textual. Soportar de forma 100% retrocompatible llamadas históricas pasando instancias directas de `bot` y enteros `chat_id`.
  - **Criterio de Aceptación:** La suite de tests existente `tests/test_worker.py` debe pasar intacta al 100%, y nuevos tests en `tests/test_worker_multichannel.py` deben validar el encolado y procesamiento en canales agnósticos usando `MockNotificationAdapter`.

- [x] **Tarea 6: Verificación Integral de Suite de Calidad y Cierre de Fase 2**
  - **Descripción:** Ejecución completa de suites de linters (`black --check`, `flake8`, `mypy`) y suite total de pruebas `pytest` (alcanzando 100% de tests aprobados sin ninguna regresión sobre los 282 tests existentes).
  - **Criterio de Aceptación:** `uv run pytest` pasa al 100% con los nuevos tests incluidos, `mypy` 0 errores, `flake8` 0 errores, `black` 0 desvíos.
