# Tareas de Implementación: Parche v1.18.2

Checklist de tareas atómicas numeradas, secuenciales e independientes. Cada tarea debe completarse y verificarse antes de pasar a la siguiente.

- [x] **Tarea 1: Reforzar guarda de tipos en `src/services/asistencia_service.py`**
  - **Acción:** En `procesar_comando_horas`, modificar la condición a `if error or not analiticas:` con mensaje de contingencia en caso de que `error` sea None.
  - **Criterio de Aceptación:** `mypy src/services/asistencia_service.py` pasa con 0 errores de indexación. (Completado: 0 errores de indexación, 20/20 tests en verde).

- [x] **Tarea 2: Anotar tipos en variables de fixtures en `tests/test_soporte.py`**
  - **Acción:** Importar `Any` de `typing` y agregar anotaciones a `self.handlers: dict[str, Any]`, `self.callback_handlers: list[Any]` y `self.msg_func_handlers: list[Any]`.
  - **Criterio de Aceptación:** `mypy tests/test_soporte.py` pasa con 0 errores `[var-annotated]`. (Completado: 0 errores en 70 archivos analizados, 3/3 tests pasando).

- [x] **Tarea 3: Incrementar versión a 1.18.2 en core, API, tests y documentación**
  - **Acción:**
    - Actualizar `VERSION` a `1.18.2`.
    - Actualizar `src/api/blueprint.py` (`health_check`) a `"version": "1.18.2"`.
    - Actualizar aserción en `tests/test_mobile_api.py` a `"1.18.2"`.
    - Registrar parche en `CHANGELOG.md` bajo `## [1.18.2] - 2026-10-28`.
    - Actualizar badge en `README.md` a `v1.18.2`.
  - **Criterio de Aceptación:** `uv run pytest tests/test_mobile_api.py` pasa en verde. (Completado: 19/19 tests pasando al 100%).

- [x] **Tarea 4: Verificación Integral de Calidad y CI Local**
  - **Acción:**
    - Ejecutar `uv run black --check .`
    - Ejecutar `uv run flake8 . --max-line-length=88 --extend-ignore=E501,W293,F821,E402,E203,F401`
    - Ejecutar `uv run mypy docs scripts src tests --no-site-packages`
    - Ejecutar `uv run pytest`
  - **Criterio de Aceptación:** 100% de los comandos finalizan con código 0. (Completado: Black PASS, Flake8 PASS, Mypy PASS 70/70 archivos, Pytest 219/219 PASS).

- [x] **Tarea 5: Auditoría Git Pre-Commit y Presentación de Gate de Despliegue**
  - **Acción:**
    - Staging selectivo por rutas explícitas (`git add <archivo>`).
    - Auditoría `git status` y `git diff --cached --stat`.
    - Generar commit `chore(release): bump version to 1.18.2 and fix typing for ci`.
    - Detenerse y presentar reporte para solicitar confirmación textual de push. (Completado).
