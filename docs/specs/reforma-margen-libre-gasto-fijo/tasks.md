# Tasks Checklist: Reforma del Margen Libre y Atributo Booleano de Gasto Fijo

---

- [x] **Tarea 1 (Constantes y Modelos Pydantic):** Añadir `Es_Gasto_Fijo` a `ENCABEZADOS_OBLIGACIONES_MAESTRO` en `src/logic/constants.py` y actualizar los modelos DTO en `src/api/schemas.py` (`ObligacionBase`, `ObligacionCreate`, `ObligacionUpdate`, `ObligacionResponse`).
  - *Criterio de Aceptación:* Modelos instanciables con `es_gasto_fijo: bool = True` por defecto y serialización correcta.

- [x] **Tarea 2 (Lógica de Dominio en `calcular_margen_de_ataque`):** Actualizar `src/logic/financiero.py` para que la suma de cuotas deducibles considere únicamente deudas activas con `Es_Gasto_Fijo` verdadero, y sanear el fallback de `routes_dashboard.py` para nunca restar gastos diarios operativos.
  - *Criterio de Aceptación:* `calcular_margen_de_ataque()` retorna el valor exacto excluyendo deudas con `Es_Gasto_Fijo = 0` y deudas pausadas.

- [x] **Tarea 3 (Soporte en Repositorio y Transiciones de Estado en Sheets):** Actualizar `SheetsRepository` (`get_obligacion_by_id`, `insertar_obligacion`, `actualizar_obligacion`) en `src/repositories/sheets_repository.py` y `routes_obligaciones.py` para persistir `Es_Gasto_Fijo` y alternarlo a `0` al pausar y `1` al reactivar, invalidando caché.
  - *Criterio de Aceptación:* `PUT /api/v1/obligaciones/{id}` con `estado="Pausado"` persiste `Es_Gasto_Fijo = 0` en Google Sheets e invalida la caché.

- [x] **Tarea 4 (Pruebas Automatizadas de Margen Libre y Gasto Fijo):** Crear suite de pruebas `tests/test_margen_libre_gasto_fijo.py` verificando el desacoplamiento de gastos diarios, el cómputo de la bandera `es_gasto_fijo` y la alternancia dinámica al pausar deudas.
  - *Criterio de Aceptación:* 100% de tests pasando en terminal sin fallas de aserción.

- [x] **Tarea 5 (Verificación Integral, Linters y Cierre de Fase):** Ejecutar la suite completa de `pytest` (superando los 464 tests), verificar linters (`flake8`, `black`) y auditar el estado limpio de Git.
  - *Criterio de Aceptación:* 0 errores de linters, suite completa aprobada y reporte final preparado para el usuario.
