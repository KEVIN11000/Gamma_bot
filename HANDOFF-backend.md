# Traspaso Backend (Gamma Mobile -> Gamma_bot)
## Requerimientos de Backend para Estabilidad y Paridad con Gamma Mobile

- **Fecha:** 29 de Octubre de 2026 (Actualizado: 30 de Octubre de 2026)
- **Origen:** Gamma Mobile (Sesión de Remediación y Estabilidad `v0.0.12` / `remediacion-estabilidad-v012`)
- **Destino:** Repositorio `Gamma_bot` (`E:\PG\vcp-s\Gamma_bot`)
- **Estado Global:** ✅ **TODOS LOS MÓDULOS RESUELTOS Y VERIFICADOS EN v1.18.6**

---

### Módulo 1: Alineación de Contratos y Esquemas (Pydantic vs Mobile) [ESTADO: RESUELTO EN v1.18.5]
1. **Soporte de Alias `"tipo"` en `POST /api/v1/movimientos` (`src/api/schemas.py`)**: `MovimientoCreate` reconoce `"tipo"` y `"monto"` con `populate_by_name = True`.
2. **Desempaquetado de `deuda_foco` en `GET /api/v1/obligaciones/foco` (`src/api/blueprint.py`)**: Atributos planos en la raíz + objeto anidado para compatibilidad total.
3. **Paridad de Clave en IA y OCR (`src/logic/ai_service.py`)**: Retorna tanto `"tipo"` como `"tipo_movimiento"`.

---

### Módulo 2: Respuestas Informativas y Códigos HTTP [ESTADO: RESUELTO EN v1.18.5]
1. **Marcación Laboral Informativa en `POST /api/v1/asistencia/marcar` (`src/api/blueprint.py`)**: Responde `HTTP 200 OK` con `tipo: "info"` y `confirmado_en_planilla: true` ante marcaciones duplicadas.
2. **Invalidación Reactiva de Caché (`src/repositories/sheets_repository.py`)**: `_sheets_cache.clear()` invocado tras cada inserción de movimiento.
3. **Cálculo de Analíticas MTD y Devengado Laboral (`src/logic/logic.py`)**: Filtrado estricto en `calcular_analiticas_asistencia` exigiendo salida confirmada para devengar salario.

---

### Módulo 3: Ejecución Real de Cierres Contables [ESTADO: RESUELTO EN v1.18.6]
1. **Reemplazo de Stub en `POST /api/v1/cierres/ejecutar` (`src/api/blueprint.py`)**:
   - Eliminadas constantes sintéticas (160h, 4.5M Gs).
   - Invocación real a `AgenteAutonomoHoras.calcular_analiticas_asistencia()` para cierres laborales y a `SheetsRepository.obtener_balance()` / `execute_monthly_closing()` para cierres contables.
2. **Sincronización de Cierres Laborales en Historial (`src/api/blueprint.py`)**: `GET /api/v1/asistencia/cierres` lista las hojas archivadas y sus comprobantes PDF.

---

### Módulo 4: Deduplicación e Idempotencia [ESTADO: RESUELTO EN v1.18.5]
1. **Recepción de `clientId` o `id` en `POST /api/v1/movimientos` (`src/api/blueprint.py`)**:
   - Ventana de idempotencia de 24 horas con `duplicado_evitado: true` ante reintentos de red del cliente móvil.

---

### Módulo 5: Realineación de Columnas y Migración en `Obligaciones_Maestro` [ESTADO: RESUELTO EN v1.18.6]
1. **Blindaje de `_ensure_headers` (`src/repositories/sheets_repository.py`)**:
   - Bloquea sobrescrituras de encabezados celda por celda si la aridad de columnas difiere de la esperada en hojas con filas de datos existentes.
2. **Script de Migración Idempotente (`scripts/migrar_obligaciones_maestro.py`)**:
   - Función determinista `realinear_fila_obligacion()` que inserta `"Deuda"` en columna B y realinea datos desfasados a las 16 columnas de `ENCABEZADOS_OBLIGACIONES_MAESTRO`.
   - Modos `--dry-run` y `--apply` disponibles para ejecución en Google Sheets.

---

### Módulo 6: Duplicación de `saldo_inicial` en Resumen de Dashboard [ESTADO: RESUELTO EN v1.18.6]
1. **Corrección de Fórmula Contable (`src/logic/financiero.py` y `src/api/blueprint.py`)**:
   - $\text{flujo\_neto} = \text{total\_ingresos} - \text{total\_gastos}$ (flujo neto operativo del período).
   - $\text{saldo\_acumulado} = \text{saldo\_inicial} + \text{flujo\_neto}$.
   - En `GET /api/v1/dashboard/summary`: `saldo_acumulado` no vuelve a sumar `saldo_inicial`, resolviendo el bug empírico donde `1.431.300 ₲` se mostraba duplicado como `2.862.600 ₲`.
