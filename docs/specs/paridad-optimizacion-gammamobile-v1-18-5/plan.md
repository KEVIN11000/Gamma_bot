# Implementation Plan: Paridad y Optimización Integral Backend con Gamma Mobile

**Branch**: `feature/paridad-optimizacion-gammamobile-v1-18-5` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

## Summary

Implementar de forma integral las adaptaciones y mejoras de paridad requeridas por Gamma Mobile documentadas en `HANDOFF-backend.md`: alineación de alias de esquemas Pydantic (`tipo`/`movimiento`), paridad dual de deuda foco y respuestas de IA/OCR, respuestas informativas HTTP 200 en marcación laboral, invalidación reactiva de caché en transacciones, deduplicación de movimientos por `client_id`, cálculo estricto de analíticas MTD y endpoint de cierres laborales.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Flask, Pydantic v2, Telebot, gspread
**Storage**: Google Sheets (Singleton), JSON temporal de idempotencia
**Testing**: pytest (`tests/test_mobile_api.py`, `tests/test_financiero.py`, etc.)
**Target Platform**: PythonAnywhere WSGI / Local

## Constitution Check

- [x] Principio rector: Verificación empírica con suite automatizada de pruebas y linters (`pytest`, `black`, `flake8`, `mypy`).
- [x] Principio de cambio mínimo necesario: Modificaciones quirúrgicas en schemas, blueprint, repository y analíticas.
- [x] Higiene de Git: Commit individualizado y barrera inviolable de despliegue hasta aprobación explícita.
- [x] SDD Gate: Todo el diseño documentado en `docs/specs/paridad-optimizacion-gammamobile-v1-18-5/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Ninguna | Patrones nativos de Flask y Pydantic | N/A |
