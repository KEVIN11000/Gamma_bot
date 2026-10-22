# Requerimientos Técnicos para el Backend Core (`Gamma_bot`) — Versión v0.2.0
## Módulo: Proyector de Capacidad de Pago, Pausado de Deudas, Historial de Cierres y Blindaje de Cuotas

- **Fecha:** 20 de Octubre de 2026
- **Versión de Requerimientos:** 0.2.0
- **Destino:** Repositorio `Gamma_bot` (`E:\PG\vcp-s\Gamma_bot`) para su desarrollo en sesión dedicada.
- **Aislamiento:** Documento exhaustivo que consolida la totalidad de adecuaciones requeridas en el backend sin alterar código fuente desde el workspace de `GammaMobile`.

---

### Requerimiento 1: `InMemorySheetsCache` en `SheetsRepository`
- **Problema:** Cada petición `GET /api/v1/dashboard/summary` ejecuta hasta 4 lecturas completas a Google Sheets (`obtener_balance()` y `calcular_margen_de_ataque()`), agotando la cuota de 60 req/min de la service account de Google Cloud (`HTTP 429 RESOURCE_EXHAUSTED`).
- **Solución Requerida:**
  1. Implementar la clase `InMemorySheetsCache` en `src/repositories/sheets_repository.py` con TTL configurable (180 segundos para balances y 300 segundos para presupuestos).
  2. Almacenar en caché las lecturas de:
     - `obtener_balance()` (clave `balance_{mes}_{año}`).
     - `get_all_movimientos()` (clave `movimientos_todos`).
     - `get_todas_obligaciones()` (clave `obligaciones_todas`).
     - `obtener_presupuesto_base_completo()` (clave `presupuesto_base`).
  3. Invalidar la clave correspondiente de inmediato al ejecutar mutaciones:
     - `insert_movimiento_diario()` $\rightarrow$ invalida `balance_` y `movimientos_`.
     - `insert_obligacion()`, `update_obligacion_saldo()` $\rightarrow$ invalida `obligaciones_` y `presupuesto_base`.

---

### Requerimiento 2: Integridad de Deudas, Abono Contable y Estado Pausado
- **Problema:** `GET /api/v1/obligaciones` descarta `Entidad`, cuotas y vencimiento; `POST /api/v1/obligaciones/abonar` no asienta el egreso contable en `Libro_Diario`; no existe mecanismo para suspender o pausar una obligación sin eliminarla.
- **Solución Requerida:**
  1. En `src/logic/constants.py`: Agregar `"Entidad"` a `ENCABEZADOS_OBLIGACIONES_MAESTRO`.
  2. En `src/repositories/sheets_repository.py`: En `insert_obligacion()`, guardar el campo `Entidad` en la columna D de la hoja `Obligaciones_Maestro`.
  3. En `src/api/blueprint.py` (`get_obligaciones`): Incluir en el diccionario JSON: `entidad`, `cuotas_totales`, `cuotas_restantes` y `dia_vencimiento`.
  4. En `src/api/blueprint.py` (`abonar_obligacion`):
     - Validar que el abono sea mayor a 0 y la deuda exista.
     - Amortizar la deuda en `Obligaciones_Maestro`.
     - Invocar `repo.insert_movimiento_diario()` con categoría `"Préstamos / Deudas"` y el monto abonado para reflejar el egreso contable en `Libro_Diario`.
     - Retirar el bloque `except` que silenciaba fallos devolviendo 200 con saldo 0.
  5. Soporte para estado `Pausado` / `Pausada`:
     - En `get_obligaciones_activas()`, `calcular_margen_de_ataque()` y `proyectar_cola_deudas()`, excluir de la pila de cuotas activas a aquellas deudas cuyo `Estado` sea `"Pausado"` o `"Pausada"`.
     - En `PUT /obligaciones/{id}`, permitir transicionar el estado entre `"Activo"` y `"Pausado"`, invalidando la caché de `obligaciones_` para recalcular el margen de ataque en el acto.

---

### Requerimiento 3: Auto-detección Dinámica de Período en `AgenteAutonomoHoras`
- **Problema:** En `src/logic/logic.py` (`AgenteAutonomoHoras.ws`), si `periodo_actual.txt` no existe, el código creaba por defecto `"Mayo 2026"` e intentaba asentar marcas de Octubre en una hoja inexistente o de Mayo, disparando llamadas de creación de hojas y consultas erróneas.
- **Solución Requerida:**
  1. Reemplazar el fallback estático `"Mayo 2026"` por la fecha actual del sistema:
     ```python
     meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
     ahora = get_now_py()
     nombre_hoja_actual = f"{meses_es[ahora.month - 1]} {ahora.year}"
     ```
  2. En `src/api/blueprint.py` (`marcar_asistencia` y `marcar_materia`):
     - Capturar específicamente `gspread.exceptions.APIError` con código 429 (`RESOURCE_EXHAUSTED`).
     - Responder con código `HTTP 429 Too Many Requests` y JSON `{ "error": { "code": "RATE_LIMIT_EXCEEDED", "message": "Servicio de Google Sheets saturado temporalmente. Espera 60 segundos antes de reintentar." } }`.

---

### Requerimiento 4: Endpoint `GET /api/v1/cierres` para Historial de Cierres Contables y Laborales
- **Problema:** Existen endpoints para ejecutar un cierre (`POST /cierres/ejecutar`) y descargar un PDF (`GET /cierres/reportes/<filename>`), pero no existe un endpoint para consultar el listado histórico de cierres realizados ni conocer los PDFs disponibles.
- **Solución Requerida:**
  1. En `src/repositories/sheets_repository.py`: Crear `get_todos_cierres_historicos() -> list[dict]` leyendo los registros de la hoja `Cierres_Historicos`.
  2. En `src/api/blueprint.py`: Implementar `@mobile_api.route("/cierres", methods=["GET"])`:
     - Retornar la lista consolidada de cierres contables (obtenidos de `Cierres_Historicos` en Sheets) y de cierres laborales (inspeccionando `REPORTES_DIR` para archivos `cierre_laboral_*.pdf` o metadatos de asistencia).
     - Esquema JSON de respuesta:
       ```json
       [
         {
           "id": "cierre_contable_octubre_2026",
           "tipo": "contable",
           "periodo": "Octubre 2026",
           "fecha": "2026-10-16 11:10",
           "total_monto": 4500000,
           "total_horas": 0.0,
           "resumen": "Ingresos: ₲ 12.000.000 | Gastos: ₲ 7.500.000",
           "pdf_url": "/api/v1/cierres/reportes/cierre_contable_octubre_2026.pdf",
           "pdf_disponible": true
         }
       ]
       ```

---

### Requerimiento 5: Endpoints de Cronograma de Vencimientos y Deuda Foco
- **Problema:** En el bot de Telegram existen `/vencimientos`, `/estrategia` y `/foco`, pero la API móvil no los exponía como endpoints estructurados.
- **Solución Requerida:**
  1. En `src/api/blueprint.py`:
     - `@mobile_api.route("/obligaciones/vencimientos", methods=["GET"])`:
       Invoca `obtener_cronograma_vencimientos()` de `financiero.py` y responde con la lista ordenada por día de vencimiento, marcando si ya venció en el mes actual.
     - `@mobile_api.route("/obligaciones/foco", methods=["GET"])`:
       Acepta parámetro query `?criterio=prioridad|saldo`. Invoca `proyectar_cola_deudas(criterio)` e identifica la deuda foco recomendada para aplicar excedentes este mes.

---

### Requerimiento 6: Motor de Proyección de Capacidad de Pago del Mes (`POST /api/v1/obligaciones/proyectar-capacidad`)
- **Problema:** El endpoint `/obligaciones/simular` solo calcula el impacto de contraer un crédito nuevo, no evalúa la capacidad de afrontar las obligaciones actuales del mes.
- **Solución Requerida:**
  1. En `src/api/blueprint.py`: Implementar `@mobile_api.route("/obligaciones/proyectar-capacidad", methods=["POST"])`:
     - Payload de entrada (opcional con overrides de simulación):
       ```json
       {
         "deudas_pausadas_simuladas": ["id_deuda_2"],
         "abonos_extraordinarios": { "id_deuda_1": 500000 },
         "ajuste_ingreso_extra": 0
       }
       ```
     - Cálculo de salida:
       * `compromiso_total_mes`: Suma de cuotas activas (excluyendo pausadas).
       * `fondo_disponible_mes`: Saldo actual en caja + ingreso base - gastos fijos.
       * `capacidad_neta`: `fondo_disponible_mes - compromiso_total_mes`.
       * `semaforo`: `"SUPERAVIT"` | `"AJUSTADO"` | `"DEFICIT"`.
       * `dti_proyectado`: Ratio de carga de deuda resultante.
       * `meses_ahorrados_por_abonos`: Estimación del impacto de los abonos simulados.
