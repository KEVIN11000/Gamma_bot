# Tasks Checklist: Proyector de Flujo de Caja, Alertas Presupuestarias y Notificaciones Push (v2.0.0 Fase 5)

---

- [x] **Tarea 1 (Motor CashFlowProjector):** Implementar `CashFlowProjector` en `src/services/cashflow_service.py` con simulación temporal de 30 días calendario, imputación de vencimientos de obligaciones fijas, estimación de gastos variables y detección de días críticos de liquidez.
  - *Criterio de Aceptación:* `tests/test_cashflow_service.py` con >= 8 pruebas unitarias validando cálculo de saldo final, días críticos ante saldo negativo y resiliencia ante obligaciones sin fecha.

- [x] **Tarea 2 (Endpoint REST Proyecciones):** Crear esquemas `FlujoCajaItemDiario` y `FlujoCajaResponse` en `src/api/schemas.py`, implementar endpoint `GET /api/v1/proyecciones/flujo-caja` en `src/api/v1/routes_proyecciones.py` protegido por `X-API-KEY` y registrarlo en `v1_bp`.
  - *Criterio de Aceptación:* `tests/test_proyecciones_routes.py` validando respuestas 200 con payload serializado, 401 si no hay API key y headers anti-cache.

- [x] **Tarea 3 (Alertas Presupuestarias Proactivas Multi-Canal):** Implementar `despachar_alerta_presupuestaria_proactiva` en `src/services/presupuesto_service.py` con formateo de advertencia en guaraníes, encolado asíncrono en `cola.db` y cooldown en memoria de 24 horas por categoría para evitar spam al usuario.
  - *Criterio de Aceptación:* `tests/test_presupuesto_alertas_service.py` comprobando emisión de alerta si supera el 80%, supresión dentro de las 24 horas de cooldown y despacho al canal correspondiente.

- [x] **Tarea 4 (Adaptador Push y Registro de Dispositivos Gamma Mobile):** Implementar `PushNotificationAdapter(INotificationPort)` en `src/adapters/notifications/push_adapter.py`, esquemas `DispositivoCreate` y `DispositivoResponse` en `src/api/schemas.py` y endpoint `POST /api/v1/dispositivos/registrar` en `src/api/v1/routes_dispositivos.py`.
  - *Criterio de Aceptación:* `tests/test_push_adapter.py` comprobando registro idempotente de tokens de dispositivos y despacho de notificaciones push simulated/HTTP.

- [x] **Tarea 5 (Verificación Global de Calidad & Cierre de Fase):** Ejecución completa de la suite de pruebas (`pytest`), formateo con `black`, linter `flake8` y verificación estricta de tipos `mypy` sin errores ni regresiones.
  - *Criterio de Aceptación:* 100% tests aprobados, 0 advertencias de linter y actualización final de `HANDOFF.md`.
