# Implementation Plan: Auto-eliminación y expiración de botoneras y mensajes en Telegram

**Branch**: `feature/auto-clean-inline-keyboards-v1-18-4` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `docs/specs/auto-clean-inline-keyboards-v1-18-4/spec.md`

## Summary

Implementar utilitarios centralizados y seguros para la auto-eliminación y remoción de teclados interactivos (`InlineKeyboardMarkup`) y mensajes transitorios de carga ("⏳ Procesando...") en Telegram (`src/com/core/utils.py`). Integrar estos helpers en los puntos críticos de interacción (menús base, flujos de confirmación de finanzas, asistencia y soporte), robusteciendo `limpiar_menus_expirados` contra excepciones de la API de Telegram y garantizando que los mensajes de confirmación permanente permanezcan intactos.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: pyTelegramBotAPI (`telebot`), Flask
**Storage**: JSON local concurrente en `data/pending_deletions.json` con Lock de threading
**Testing**: pytest (`tests/test_utils.py`, `tests/test_handlers_*.py`)
**Target Platform**: Linux (PythonAnywhere WSGI) y Windows local
**Project Type**: Telegram Bot / Webhook Backend
**Performance Goals**: <50ms de latencia en remoción de markup sin llamadas bloqueantes en red
**Constraints**: Resiliencia total ante excepciones de Telegram API (`message to delete not found`, `message is not modified`, `message can't be deleted`)

## Constitution Check

- [x] Principio rector: Verificación empírica con tests automatizados (`pytest tests/`).
- [x] Principio de cambio mínimo necesario: Modificaciones quirúrgicas limitadas a `src/com/core/utils.py` y llamadas puntuales en handlers donde se cierran flujos.
- [x] Higiene de Git: No `git add .`, solo archivos versionados explícitamente; exclusión de archivos efímeros.
- [x] SDD Gate: Documentación desacoplada en `docs/specs/auto-clean-inline-keyboards-v1-18-4/`.

## Project Structure

### Documentation (this feature)

```text
docs/specs/auto-clean-inline-keyboards-v1-18-4/
├── spec.md              # Especificación funcional y criterios de éxito
├── research.md          # Decisiones técnicas y alternativas evaluadas
├── data-model.md        # Estructura de PendingDeletion y TransientMessage
├── quickstart.md        # Guía de validación de escenarios
├── contracts/
│   └── helpers_contrato.md # Firmas y contratos de las funciones auxiliares
├── plan.md              # Este plan de implementación
└── tasks.md             # Tareas atómicas ordenadas por historias
```

### Source Code (repository root)

```text
src/com/core/
├── utils.py             # Helpers seguros: eliminar_mensaje_seguro, remover_teclado_inline, limpiar_menus_expirados con Lock

src/com/handlers/
├── base.py              # Remoción de teclados en menús interactivos
├── finanzas.py          # Limpieza de mensajes de carga OCR y menús de categoría
├── asistencia.py        # Limpieza de botonera tras selección de marcación
└── soporte.py           # Remoción de markup tras confirmación de ticket

tests/
├── test_utils.py        # Pruebas unitarias de helpers y concurrencia de pending_deletions
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Ninguna | Arquitectura estándar y ligera | N/A |
