# Plan de Arquitectura e Implementación: Parche v1.18.2

## 1. Diagnóstico Detallado de Fallos

### 1.1 `src/services/asistencia_service.py`
* **Línea:** 344-360
* **Causa raíz:** La función `obtener_analiticas_horas` retorna la tupla `Tuple[Optional[Dict[str, Any]], Optional[str]]`. Al evaluar únicamente `if error:`, `mypy` no puede inferir con certeza estricta que `analiticas` no sea `None`. Al acceder subsecuentemente a `analiticas["periodo"]`, se desencadenan 13 advertencias de tipo `[index]`.
* **Solución técnica:**
  ```python
  if error or not analiticas:
      bot.reply_to(message, str(error or "Módulo de horas no disponible."))
      return
  ```
  Esto reduce el tipo de `analiticas` de `Optional[Dict[str, Any]]` a `Dict[str, Any]` garantizando seguridad de tipos estática y robustez en tiempo de ejecución.

### 1.2 `tests/test_soporte.py`
* **Línea:** 22-24
* **Causa raíz:** En el método `setUp`, las variables de instancia `self.handlers = {}`, `self.callback_handlers = []`, `self.msg_func_handlers = []` se inicializan sin anotaciones de tipo explícitas requeridas por `mypy` (`[var-annotated]`).
* **Solución técnica:**
  ```python
  from typing import Any
  ...
  self.handlers: dict[str, Any] = {}
  self.callback_handlers: list[Any] = []
  self.msg_func_handlers: list[Any] = []
  ```

---

## 2. Estrategia de Versionado Semántico y Contratos

| Archivo | Cambio Proyectado | Justificación |
| :--- | :--- | :--- |
| `VERSION` | `1.18.2` | Bump de versión de parche. |
| `src/api/blueprint.py` | `"version": "1.18.2"` | Contrato del endpoint `/health` consumido por GammaMobile y monitoreo. |
| `tests/test_mobile_api.py` | `assert data["version"] == "1.18.2"` | Validación automatizada de paridad de versión en API. |
| `README.md` | Badge `v1.18.2` | Documentación oficial del repositorio. |
| `CHANGELOG.md` | Entrada `## [1.18.2] - 2026-10-28` | Trazabilidad bajo convención *Keep a Changelog*. |

---

## 3. Plan de Pruebas y Validación Empírica
1. **Linter Black:** `uv run black --check .`
2. **Linter Flake8:** `uv run flake8 . --max-line-length=88 --extend-ignore=E501,W293,F821,E402,E203,F401`
3. **Comprobación Estática Mypy:** `uv run mypy docs scripts src tests --no-site-packages`
4. **Suite Completa Pytest:** `uv run pytest` (219 tests).
5. **Auditoría Git:** `git status` y `git diff --cached --stat` antes de solicitar aprobación final de despliegue.
