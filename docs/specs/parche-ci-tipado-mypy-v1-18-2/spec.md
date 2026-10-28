# Especificación Técnica: Parche de Calidad de Tipado y CI (v1.18.2)

## 1. Contexto y Objetivos
En la ejecución del flujo de integración continua (CI) en GitHub Actions (`ubuntu-latest`), el trabajo `lint` ejecuta secuencialmente:
1. `black --check .`
2. `flake8 . --max-line-length=88 --extend-ignore=E501,W293,F821,E402,E203,F401`
3. `mypy . --no-site-packages`

El paso 3 (`mypy`) falla con código de salida 1 debido a 16 errores de tipado estático detectados en 2 archivos:
* 13 errores de indexación en `src/services/asistencia_service.py` (`Value of type "Any | None" is not indexable`).
* 3 errores de falta de anotación de tipo en variables de prueba en `tests/test_soporte.py` (`Need type annotation for ...`).

El objetivo es aplicar una resolución formal vía parche versionado (`1.18.2`), respetando el ciclo SDD estricto sin parches improvisados (*no hotfixes*), garantizando el paso en verde del 100% de los jobs de CI en entornos Ubuntu/Linux y Windows.

---

## 2. Alcance (In-Scope)
* **Guardas de Tipo Estricto en Asistencia:**
  * Reforzar la comprobación en `src/services/asistencia_service.py` (`procesar_comando_horas`) para asegurar estrechamiento de tipo (`type narrowing`) de `analiticas` ante `Optional[Dict[str, Any]]`.
* **Anotación Explícita en Tests:**
  * Declarar anotaciones de tipo (`dict[str, Any]`, `list[Any]`) en `tests/test_soporte.py` para satisfacer `mypy`.
* **Incremento Oficial de Versión:**
  * Incrementar la versión semántica de `1.18.1` a `1.18.2` (Patch release).
  * Actualizar `VERSION`, `src/api/blueprint.py`, `tests/test_mobile_api.py`, `README.md` y `CHANGELOG.md`.
* **Verificación Empírica:**
  * Ejecución local completa de `black`, `flake8`, `mypy` y `pytest` antes de cualquier entrega.

---

## 3. Fuera de Alcance (No-Scope)
* Modificaciones de lógica de negocio o formato de reportes de asistencia / Excel / PDF.
* Modificaciones en archivos excluidos o repositorios auxiliares (`repositories/`).
* Alteración del esquema de base de datos o endpoints REST fuera del reporte de versión de `/health`.

---

## 4. Criterios de Aceptación
1. `mypy docs scripts src tests --no-site-packages` finaliza con código de salida 0 y 0 errores.
2. `flake8 . --max-line-length=88 --extend-ignore=E501,W293,F821,E402,E203,F401` finaliza con código de salida 0.
3. `black --check .` finaliza con código de salida 0.
4. `pytest` ejecuta los 219 tests unitarios e integrados pasando al 100%.
5. La versión `1.18.2` queda documentada en `CHANGELOG.md` y sincronizada en los contratos de la API.
