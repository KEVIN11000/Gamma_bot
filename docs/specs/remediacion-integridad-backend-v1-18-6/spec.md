# Feature Specification: Remediación de Integridad y Paridad Backend con Gamma Mobile

**Feature Branch**: `feature/remediacion-integridad-backend-v1-18-6`  
**Created**: 2026-10-30  
**Status**: Draft  
**Target Release**: `v1.18.6`  
**Inputs**:
- `E:\PG\vcp-s\GammaMobile\HANDOFF-backend.md` (Módulos 3.1, 5 y 6)
- `E:\PG\vcp-s\Gamma_bot\HANDOFF.md` (Pendientes de cierre contable y verificación de paridad)

---

## 1. Alcance y Objetivos

Esta especificación cubre la resolución definitiva de las inconsistencias contables y estructurales detectadas en la integración entre `Gamma_bot` y `Gamma Mobile`:

1. **Corrección de Duplicación de `saldo_inicial` (Módulo 6)**: Corregir la definición contable de `flujo_neto` y `saldo_acumulado` para evitar la duplicación de saldos de apertura en `GET /api/v1/dashboard/summary`.
2. **Reparación Estructural y Migración de `Obligaciones_Maestro` (Módulo 5)**:
   - Proveer un script de migración determinista que detecte y realinee las columnas de datos desfasadas en la hoja `Obligaciones_Maestro`.
   - Robustecer `SheetsRepository._ensure_headers` para impedir sobrescrituras de encabezados destructivas cuando los datos no tengan la paridad columnar esperada.
3. **Ejecución Real de Cierres en API (Módulo 3.1)**:
   - Sustituir el stub hardcodeado (160h, 4.5M Gs) en `POST /api/v1/cierres/ejecutar` por la llamada real al motor de cierre contable y laboral, generando comprobantes y registros históricos verídicos.

---

## 2. Casos de Uso y Escenarios de Aceptación

### User Story 1 - Consistencia Financiera en Dashboard (Priority: P1) 🎯 MVP

Como usuario de Gamma Mobile, al abrir la pantalla de inicio, quiero que el balance acumulado y el flujo neto reflejen la realidad contable de mi libro diario sin duplicar el saldo inicial, para no tomar decisiones basadas en números inflados.

- **Independent Test**: Ejecutar `AgenteFinanciero.obtener_balance()` y `GET /api/v1/dashboard/summary` con un asiento de apertura de `1.431.300 ₲` y verificar que el `saldo_acumulado` sea `1.431.300 ₲` y el `flujo_neto` sea `0 ₲` (en ausencia de otros movimientos).
- **Escenarios de Aceptación**:
  1. **Given** un `Libro_Diario` con `saldo_inicial = 1.431.300 ₲`, `ingresos = 500.000 ₲` y `gastos = 200.000 ₲`.
  2. **When** se consulta `GET /api/v1/dashboard/summary`.
  3. **Then** la respuesta debe contener:
     - `flujo_neto = 300.000` (ingresos - gastos).
     - `saldo_acumulado = 1.731.300` (saldo_inicial + flujo_neto).
     - `saldo_inicial = 1.431.300`.

---

### User Story 2 - Blindaje y Migración de `Obligaciones_Maestro` (Priority: P1)

Como sistema y usuario administrativo, quiero que los encabezados y las filas de datos de `Obligaciones_Maestro` mantengan una correspondencia 1:1 con `ENCABEZADOS_OBLIGACIONES_MAESTRO`, para que los nombres de entidades, cuotas y saldos no se mezclen ni devuelvan valores numéricos en campos de texto o ceros en saldos activos.

- **Independent Test**: Ejecutar el script de migración sobre fixtures de datos con y sin la columna `Tipo` y verificar que las filas queden perfectamente alineadas. Invocar `_ensure_headers` en una hoja desfasada y comprobar que no destruya la correlación columna-dato.
- **Escenarios de Aceptación**:
  1. **Given** una fila histórica en `Obligaciones_Maestro` con estructura antigua `[ID, Nombre, Entidad, Monto_Inicial, Saldo_Actual, Estado, ...]`.
  2. **When** se ejecuta el script de migración `scripts/migrar_obligaciones_maestro.py`.
  3. **Then** la fila se transforma en `[ID, "Deuda", Nombre, Entidad, Monto_Inicial, Saldo_Actual, Estado, ...]`, restaurando la paridad con `ENCABEZADOS_OBLIGACIONES_MAESTRO`.
  4. **Given** `_ensure_headers` en `SheetsRepository`.
  5. **When** se evalúa una hoja con encabezados discordantes pero con filas de datos preexistentes de longitud menor.
  6. **Then** la función registra una alerta sin alterar ciegamente las celdas individuales para evitar desfases silenciosos.

---

### User Story 3 - Cierre Contable y Laboral Real vía API (Priority: P2)

Como administrador desde la aplicación móvil, quiero presionar "Ejecutar Cierre" y que el sistema procese el período real leyendo la planilla de Google Sheets, archivando el registro histórico y emitiendo el PDF correspondiente, sin usar valores sintéticos inventados.

- **Independent Test**: Invocar `POST /api/v1/cierres/ejecutar` con `{"tipo": "contable", "hoja": "Octubre 2026"}` y verificar que procese los asientos de la hoja, escriba en `Cierres_Historicos` o genere el reporte contable real.
- **Escenarios de Aceptación**:
  1. **Given** un payload `{"tipo": "contable", "hoja": "..."}`.
  2. **When** se envía a `POST /api/v1/cierres/ejecutar`.
  3. **Then** el endpoint invoca a `AgenteExcel` / `execute_monthly_closing`, genera el PDF real en `data/reportes/` y retorna `200 OK` con el resumen financiero verídico.
  4. **Given** un payload `{"tipo": "horas", "hoja": "..."}`.
  5. **When** se envía a `POST /api/v1/cierres/ejecutar`.
  6. **Then** el endpoint computa las horas efectivas y salario devengado real desde la hoja de asistencia correspondiente.

---

## 3. Lo que Queda Excluido (No-Scope)

1. No se modificará el contrato de esquemas consumidos por Gamma Mobile (la app continuará esperando los mismos nombres de campos DTO ya estandarizados).
2. No se alterarán los flujos conversacionales de Telegram existentes salvo donde compartan módulos de cálculo financiero o cierre.
3. No se ejecutarán scripts destructivos en Google Sheets productivo sin confirmación explícita o modo `--dry-run`.
