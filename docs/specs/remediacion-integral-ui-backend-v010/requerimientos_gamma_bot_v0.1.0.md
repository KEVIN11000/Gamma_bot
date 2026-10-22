# Requerimientos Técnicos para el Backend Core (`Gamma_bot`)
## Módulo: Remediación Integral UI/UX, Backend Contracts, Estabilización de Marcación y Blindaje de Cuotas Google Sheets (v0.1.0)

- **Fecha:** 20 de Octubre de 2026
- **Destino:** Repositorio `Gamma_bot` (`E:\PG\vcp-s\Gamma_bot`) para su desarrollo en sesión dedicada.
- **Aislamiento:** Este documento decanta todas las modificaciones requeridas en el backend sin alterar código fuente desde el workspace móvil de `GammaMobile`.

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

### Requerimiento 2: Integridad de Deudas y Contabilidad de Abonos
- **Problema:** `GET /api/v1/obligaciones` descarta `Entidad`, cuotas y vencimiento; `POST /api/v1/obligaciones/abonar` no registra el egreso en `Libro_Diario` y enmascara errores con un `200 OK` ficticio de saldo 0.
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
     - En `PUT /obligaciones/{id}`, permitir transicionar el estado entre `"Activo"` y `"Pausado"`, invalidando la caché de `obligaciones_` para recalcular el margen de ataque de inmediato.

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
- **Problema:** En `src/api/blueprint.py` existen endpoints para ejecutar un cierre (`POST /cierres/ejecutar`) y descargar un PDF (`GET /cierres/reportes/<filename>`), pero no existe un endpoint para consultar el listado histórico de cierres realizados ni conocer los PDFs disponibles para su visualización en la app móvil.
- **Solución Requerida:**
  1. En `src/repositories/sheets_repository.py`: Crear `get_todos_cierres_historicos() -> list[dict]` leyendo todos los registros de la hoja `Cierres_Historicos`.
  2. En `src/api/blueprint.py`: Implementar `@mobile_api.route("/cierres", methods=["GET"])`:
     - Retornar la lista consolidada de cierres contables (obtenidos de `Cierres_Historicos` en Sheets) y de cierres laborales (inspeccionando `REPORTES_DIR` para archivos `cierre_laboral_*.pdf` o metadatos de asistencia).
     - Cada elemento del JSON debe estructurarse como:
       ```json
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
       ```
