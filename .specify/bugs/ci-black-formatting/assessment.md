# Bug Assessment: Falla en Pipeline CI/CD por Formato Black

- **Slug**: ci-black-formatting
- **Created**: 2026-10-13T12:30:00-03:00
- **Source**: GitHub Issue #6 (`GHI-6`) y Run de GitHub Actions #37510795387 (`CI-37510795387`)
- **Verdict**: valid
- **Severity**: high

## Report (verbatim or summarized)

> "Fallo detectado en workflow 'CI/CD' para la rama Main-stable. Run #37510795387 en commit a5075fba. Job 'lint' falló en el paso 'Lint with black'."

## Symptom

El pipeline de GitHub Actions falla en el job `lint` impidiendo que los commits en `Main-stable` pasen el control de calidad, debido a que `src/flask_app.py` y `tests/test_soporte.py` no estaban formateados según las reglas estrictas de `black`.

## Reproduction

1. Ejecutar `black --check src tests` en la raíz del proyecto.
2. Observar el error: `would reformat src\flask_app.py`, `would reformat tests\test_soporte.py` (exit code 1).

## Suspected Code Paths

- `src/flask_app.py`
- `tests/test_soporte.py`

## Root Cause Hypothesis

En el commit `a5075fba` se agregaron modificaciones en `src/flask_app.py` y `tests/test_soporte.py` sin pasar previamente el formateador automático `black`. Como el workflow de GitHub Actions (`.github/workflows/ci.yml`) corre `black --check .`, el job de linting falló.

## Proposed Remediation

1. Formatear `src/flask_app.py` y `tests/test_soporte.py` con `black`.
2. Validar con `black --check src tests`, `flake8` y `mypy`.
3. Ejecutar suite de pruebas completa para descartar cualquier impacto funcional.

## Risks & Considerations

- Solo cambios cosméticos / de formato, riesgo funcional nulo.
