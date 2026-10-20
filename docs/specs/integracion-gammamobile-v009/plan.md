# Implementation Plan: Integración GammaMobile v0.0.9 en el Core Gamma_bot

**Branch**: `Main-stable` (trabajo en rama / feature `integracion-gammamobile-v009`) | **Date**: 2026-10-20 | **Spec**: [spec.md](file:///E:/PG/vcp-s/Gamma_bot/docs/specs/integracion-gammamobile-v009/spec.md)

**Input**: Requerimientos decantados en `repositories/Main-stable/docs/specs/GammaMobile v0.0.9/requerimientos_gamma_bot.md` y especificación funcional en `docs/specs/integracion-gammamobile-v009/spec.md`.

---

## Summary

Adecuar el core del sistema de gestión (`Gamma_bot`) para dar soporte completo a los contratos y flujos requeridos por la versión móvil `GammaMobile v0.0.9`:
1. Marcación laboral real en Google Sheets vía `AgenteAutonomoHoras` con manejo de estados semánticos (400/409 vs 200).
2. Pipeline dinámico de balance y margen de ataque con cálculo tributario en movimientos y cabeceras anti-caché.
3. Sincronización real con Google Calendar y CRUD completo de avisos (`POST`, `PUT`, `DELETE`).
4. Soporte nativo para obligaciones simuladas y activas (`POST`, `PUT`, `DELETE`) con evaluación de margen real.
5. Buffer circular de logs del servidor en tiempo real leyendo `gen_log.txt`.

---

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: Flask, Pydantic, gspread, google-api-python-client  
**Storage**: Google Sheets API, Google Calendar API, `src/avisos.json`, `src/gen_log.txt`  
**Testing**: pytest (suite existente de 188 tests), mocks de gspread y Calendar  
**Target Platform**: Linux WSGI (PythonAnywhere) & Windows local  
**Project Type**: Backend Web Service / Telegram Bot  
**Performance Goals**: < 800ms para endpoints de resumen y logs, tolerancia a fallos de red en llamadas a Google APIs  
**Constraints**: Entorno WSGI sin worker daemon permanente, política de cambio mínimo necesario, sin alterar handlers de Telegram  
**Scale/Scope**: 5 endpoints modificados, 4 endpoints nuevos/ampliados en `src/api/blueprint.py`, esquemas Pydantic en `src/api/schemas.py`, métodos complementarios en `src/repositories/sheets_repository.py`  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principio I: Calidad y Verificación Empírica ante Todo**: Toda modificación debe acompañarse de tests en `tests/test_mobile_api.py` ejecutados en la terminal. -> **PASS**
- **Principio II: Minimal Change**: Cambios quirúrgicos limitados a `blueprint.py`, `schemas.py`, `sheets_repository.py` y tests. -> **PASS**
- **Principio III: Fuga Cero e Higiene Git**: Ningún archivo sensible modificado, staging individual sin `git add .`. -> **PASS**
- **Principio IV: SDD (Fase 0 Gate)**: Generación de `spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`. No tocar código fuente `.py` hasta recibir confirmación explícita del usuario. -> **PASS**

---

## Project Structure

### Documentation (this feature)

```text
docs/specs/integracion-gammamobile-v009/
├── spec.md              # Requerimientos funcionales y criterios de aceptación
├── plan.md              # Este plan de implementación arquitectónico
├── research.md          # Fase 0: Decisiones y alternativas evaluadas
├── data-model.md        # Fase 1: Esquemas Pydantic y entidades
├── contracts/           # Fase 1: Especificación OpenAPI 3.0
│   └── openapi.yaml
├── quickstart.md        # Fase 1: Guía ejecutable de validación de escenarios
└── tasks.md             # Fase 0 Gate: Checklist atómico de tareas para implementación
```

### Source Code Impacted

```text
src/
├── api/
│   ├── blueprint.py     # Endpoints de API Mobile (asistencia, dashboard, avisos, obligaciones, logs)
│   └── schemas.py       # Esquemas de validación Pydantic (AvisoCreate/Update, ObligacionCreate/Update)
├── repositories/
│   └── sheets_repository.py # Métodos delete_obligacion y update_obligacion_general
└── services/
    └── calendar_service.py  # Delegación a AgenteAutonomoHoras para eventos Calendar

tests/
└── test_mobile_api.py   # Suite de pruebas unitarias y de integración para los nuevos contratos
```

**Structure Decision**: El proyecto es un monolito modular en `src/`. La API para el cliente móvil reside en `src/api/blueprint.py` y consume directamente los servicios de dominio y repositorios existentes (`logic/`, `repositories/`).

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Ninguna | N/A | No se introducen patrones complejos ni nuevas bases de datos; se extienden los esquemas y repositorios existentes. |

---

## Next Steps

1. Presentar el plan al usuario y solicitar confirmación para avanzar al checklist de tareas atómicas (`tasks.md`).
2. Tras la aprobación del Gate de Fase 0, ejecutar la implementación tarea por tarea bajo TDD (test $\rightarrow$ implementación $\rightarrow$ validación de linters).
