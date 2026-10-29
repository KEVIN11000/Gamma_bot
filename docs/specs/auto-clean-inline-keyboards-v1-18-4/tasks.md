# Tasks: Auto-eliminación y expiración de botoneras y mensajes en Telegram

**Input**: Design documents from `docs/specs/auto-clean-inline-keyboards-v1-18-4/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Ejecutable en paralelo
- **[Story]**: Historia de usuario (US1: Limpieza inmediata, US2: Expiración resiliente, US3: Preservación de comprobantes)

---

## Phase 1: Foundational (Infraestructura de Utilidades Core)

- [x] T001 [US2] Proteger la persistencia de `src/data/pending_deletions.json` con `threading.Lock` en `src/com/core/utils.py` para evitar corrupción por concurrencia.
- [x] T002 [US1] Implementar `eliminar_mensaje_seguro(bot, chat_id, message_id)` en `src/com/core/utils.py` con manejo defensivo de excepciones de Telebot.
- [x] T003 [US1] Implementar `remover_teclado_inline(bot, chat_id, message_id)` en `src/com/core/utils.py` utilizando `edit_message_reply_markup(reply_markup=None)`.
- [x] T004 [US2] Robustecer `limpiar_menus_expirados(bot)` en `src/com/core/utils.py` para tolerar errores silenciosamente y soportar la estructura de diccionario de `PendingDeletion`.
- [x] T005 [P] [US1] Añadir pruebas unitarias completas para los nuevos helpers en `tests/test_utils.py`.

---

## Phase 2: User Story 1 - Limpieza inmediata en flujos interactivos (Priority: P1) 🎯 MVP

- [x] T006 [US1] Integrar `remover_teclado_inline` en handlers de menús de navegación en `src/com/handlers/base.py` al seleccionar una acción.
- [x] T007 [US1] Integrar remoción de teclado y limpieza de mensaje transitorio de carga en flujos OCR / registro rápido en `src/com/handlers/finanzas.py`.
- [x] T008 [US1] Integrar remoción de teclado tras confirmación de marcación laboral en `src/com/handlers/asistencia.py`.
- [x] T009 [US1] Integrar remoción de teclado tras envío o confirmación de ticket en `src/com/handlers/soporte.py`.

---

## Phase 3: User Story 3 & QA (Priority: P3 / Regresión)

- [x] T010 [US3] Validar que las confirmaciones permanentes de gastos, marcaciones y balances no invocan borrado automático en los tests existentes.
- [x] T011 Ejecutar suite completa de tests (`pytest`), formato (`black`) y linters (`flake8`, `mypy`).
