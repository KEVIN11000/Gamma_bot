# Technical Plan: Remediación de Integridad y Paridad Backend

**Feature Branch**: `feature/remediacion-integridad-backend-v1-18-6`  
**Spec Document**: `docs/specs/remediacion-integridad-backend-v1-18-6/spec.md`  
**Target Release**: `v1.18.6`

---

## 1. Arquitectura Modular y Componentes Involucrados

```
+-----------------------------------------------------------------------------------+
|                                GAMMA MOBILE CLIENT                                |
+-----------------------------------------------------------------------------------+
           |                                       |                         |
   GET /dashboard/summary            POST /cierres/ejecutar       GET /obligaciones
           v                                       v                         v
+-----------------------------------------------------------------------------------+
|                             src/api/blueprint.py                                  |
| - get_dashboard_summary():                                                        |
|     * Calcula saldo_acumulado = balance['saldo_acumulado']                         |
| - ejecutar_cierre():                                                              |
|     * Reemplaza stub 160h/4.5M por invocación a AgenteExcel / AgenteAutonomoHoras |
+-----------------------------------------------------------------------------------+
           |                                       |
           v                                       v
+----------------------------------+   +--------------------------------------------+
|     src/logic/financiero.py      |   |            src/logic/agente_excel.py       |
| - obtener_balance():             |   | - ejecutar_cierre_periodo_manual()         |
|   flujo_neto = ingresos - gastos |   |   o execute_monthly_closing()              |
|   saldo_acumulado =              |   +--------------------------------------------+
|     saldo_inicial + flujo_neto   |
+----------------------------------+
           |
           v
+-----------------------------------------------------------------------------------+
|                     src/repositories/sheets_repository.py                         |
| - _ensure_headers(): verificación de compatibilidad de ancho antes de actualizar  |
| - scripts/migrar_obligaciones_maestro.py: migración segura con backup y dry-run   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Contratos de Datos y Esquemas

### 2.1. Contrato `GET /api/v1/dashboard/summary`
```json
{
  "saldo_acumulado": 1731300,
  "saldo_inicial": 1431300,
  "ingresos": 500000,
  "gastos": 200000,
  "flujo_neto": 300000,
  "margen_libre": 260000,
  "posicion_iva": 0,
  "es_debito_fiscal": false,
  "mes_actual": "Octubre",
  "periodo_cerrado": false
}
```
**Regla Contable**:
$$\text{flujo\_neto} = \text{ingresos} - \text{gastos}$$
$$\text{saldo\_acumulado} = \text{saldo\_inicial} + \text{flujo\_neto}$$
Se prohíbe terminantemente sumar `saldo_inicial` dos veces.

---

### 2.2. Contrato `POST /api/v1/cierres/ejecutar`
**Request Body**:
```json
{
  "tipo": "contable", // o "horas"
  "hoja": "Octubre 2026",
  "aplicar_descuento": false
}
```

**Response Body (200 OK)**:
```json
{
  "status": "success",
  "tipo": "contable",
  "periodo": "Octubre 2026",
  "totales": {
    "ingresos": 500000,
    "gastos": 200000,
    "flujo_neto": 300000,
    "total_horas": 0.0,
    "monto_liquidado": 300000
  },
  "pdf_url": "/api/v1/reportes/descargar/cierre_contable_octubre_2026.pdf",
  "archivo_backup": "Cierre_Contable_Octubre_2026.xlsx",
  "mensaje": "Cierre contable procesado exitosamente"
}
```

---

### 2.3. Esquema Tabular `Obligaciones_Maestro`
Encabezados canónicos definidos en `src/logic/constants.py`:
1. `ID_Obligacion`
2. `Tipo` (Ej: `"Deuda"`, `"Prestamo"`, `"Gasto Fijo"`)
3. `Nombre`
4. `Entidad`
5. `Monto_Inicial`
6. `Saldo_Actual`
7. `Estado`
8. `Cuota_Referencia_Gs`
9. `Fecha_Inicio`
10. `Observaciones`
11. `Cuotas`
12. `Event_ID`
13. `Dia_Vencimiento`
14. `Cuotas_Totales`
15. `Cuotas_Restantes`
16. `Orden_Prioridad`

**Lógica de Migración**:
Si la cabecera preexistente o la primera fila de datos tiene 15 columnas y la columna 2 contiene un nombre descriptivo (no un tipo canónico), se desplaza cada fila insertando `"Deuda"` en el índice 2 (columna B).

---

## 3. Manejo de Errores y Seguridad

1. **Migración Idempotente y con Dry-Run**:
   - `scripts/migrar_obligaciones_maestro.py` contará con flags `--dry-run` y `--apply`.
   - Si una fila ya cuenta con 16 columnas y un valor válido en la columna `Tipo`, no se tocará.
2. **Robustecimiento de `_ensure_headers`**:
   - Si `len(first_row) < len(expected)` y la hoja contiene datos (`ws.row_count > 1`), `_ensure_headers` registrará un log de advertencia y **no** sobrescribirá la fila 1 de forma destructiva sin intervención de migración.
3. **Manejo de Excepciones en Cierres**:
   - Si la hoja solicitada no existe o no contiene registros válidos para liquidar, el endpoint retornará un `400 Bad Request` o `422 Unprocessable Entity` con detalle estructurado en lugar de caer en 500.

---

## 4. Estrategia de Pruebas

1. **Unit Tests**:
   - `tests/test_balance_dashboard.py`: Validar la fórmula contable de `flujo_neto` y `saldo_acumulado` asegurando cero duplicidad del saldo inicial.
   - `tests/test_migracion_obligaciones.py`: Validar que el transformador de filas alinee correctamente estructuras legacy a la estructura canónica de 16 columnas.
   - `tests/test_ensure_headers.py`: Validar que `_ensure_headers` no rompa hojas con datos de diferente ancho.
   - `tests/test_cierres_api.py`: Validar que `/cierres/ejecutar` delegue a la lógica contable real y retorne datos coherentes.
2. **Quality Gates**:
   - `black --check .`
   - `flake8 . --max-line-length=88 ...`
   - `mypy docs scripts src tests --no-site-packages`
   - `pytest` (227+ tests en verde).
