# Tasks Checklist: Parser Conversacional de Lenguaje Natural, Rate-Limiting Webhooks y Extensiones UI para Gamma Mobile (v2.0.0 Fase 4)

---

- [x] **Tarea 1 (NLP Financiero):** Implementar `FinanceNLParser` en `src/utils/nlp_parser.py` con extracción determinista de montos (`k`, `M`, separadores de miles paraguayos/internacionales), detección de tipo (Gasto/Ingreso), mapeo de categorías estándar y extracción de comercios/proveedores.
  - *Criterio de Aceptación:* `tests/test_nlp_parser.py` con >= 15 pruebas unitarias cubriendo variaciones de texto informal ("gasto 45.000 Don Vito", "15k en biggie", "ingreso 2M sueldo", "compre cafe 20000"). Cobertura 100% verde en pytest.

- [x] **Tarea 2 (Endpoint REST Parsing):** Añadir esquemas DTO `ParseMovementRequest` y `ParsedMovement` en `src/api/schemas.py` y montar endpoint `POST /api/v1/movimientos/parse` en `src/api/v1/routes_movimientos.py` protegido por `X-API-KEY`.
  - *Criterio de Aceptación:* `tests/test_nlp_routes.py` validando respuestas 200 con payload parsed, manejo de validación 422 para texto vacío y 401 si no hay API key.

- [x] **Tarea 3 (Hardening & Rate Limiting en Webhooks):** Configurar limitación de tasa (60 req/min por IP) y control de tamaño máximo en `POST /api/v1/webhooks/whatsapp` en `src/api/v1/routes_webhooks.py` y `src/api/security.py`.
  - *Criterio de Aceptación:* `tests/test_webhook_rate_limiting.py` confirmando que peticiones en ráfaga devuelven HTTP 429 Too Many Requests sin tocar la base de datos `cola.db`.

- [x] **Tarea 4 (Procesamiento End-to-End en Worker WhatsApp):** Conectar `FinanceNLParser` dentro de `src/app_queue/worker.py` en la operación `"procesar_mensaje_whatsapp"`. Si es un movimiento válido, registrarlo y responder con confirmación detallada con emojis; si no es financiero, emitir saludo/guía de ayuda.
  - *Criterio de Aceptación:* `tests/test_worker_whatsapp_chat.py` verificando el flujo de recepción, parseo, registro contable y despacho de respuesta al usuario.

- [x] **Tarea 5 (Extensiones UI & Reality Checker Gamma Mobile):** Diseñar especificación de interfaz y mockup visual interactivo (Generative UI / Compose Preview spec) de `WeatherForecastCard` (consumiendo `GET /api/v1/clima`) y `QuickAttendanceWidget` (marcación rápida con área táctil >= 48dp y debounce).
  - *Criterio de Aceptación:* Verificación visual empírica de ergonomía, accesibilidad de contrastes, jerarquía tipográfica y estados (Loading, Ready, Error).

- [x] **Tarea 6 (Verificación Global de Calidad & Cierre de Fase):** Ejecución completa de la suite de pruebas (`pytest`), formateo con `black`, linter `flake8` y verificación estricta de tipos `mypy` sin errores ni regresiones.
  - *Criterio de Aceptación:* 100% tests aprobados, 0 advertencias de linter y actualización final de `HANDOFF.md`.
