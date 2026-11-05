# Especificación Funcional: Endpoint de Rectificación y Corrección de Jornada Laboral

**Feature:** `rectificacion-jornada-asistencia`  
**Fecha:** 2026-11-05  
**Prioridad:** Alta  
**Estado:** Fase 0 — Especificación y Arquitectura  

---

## 1. Contexto y Justificación del Requerimiento
Actualmente, las marcaciones de asistencia laboral se registran en tiempo real mediante el bot de Telegram o la app móvil hacia la base de datos local SQLite (`gamma_local.db`). Cuando ocurre un olvido, un error al marcar (ej. registrar la salida al final del día habiendo omitido la entrada) o una inconsistencia humana, no existe un mecanismo formal y seguro para rectificar el registro en el servidor sin manipular archivos manualmente.

A fin de mes, el servidor genera las planillas de asistencia (Excel/PDF) leyendo directamente de la base de datos y de la planilla oficial de Google Sheets. Para garantizar que los reportes impresos y consolidados sean 100% fidedignos y correctos, es imprescindible contar con un endpoint autenticado (`PUT /api/v1/asistencia/jornadas/<fecha>`) que permita actualizar y consolidar los horarios de una fecha puntual y propagarlos de inmediato a Google Sheets.

---

## 2. Alcance (In-Scope)
1. **Endpoint REST Autenticado:**
   - Ruta: `PUT /api/v1/asistencia/jornadas/<fecha>` (donde `<fecha>` es ISO `YYYY-MM-DD`).
   - Seguridad: Requerimiento obligatorio de cabecera `X-API-KEY`.
2. **Actualización Segura de Jornada en SQLite:**
   - Permite definir o modificar de forma explícita: `hora_entrada`, `hora_salida_almuerzo`, `hora_vuelta_almuerzo`, `hora_salida` y `modo` (`normal` | `directo`).
   - Si la jornada de esa fecha no existía en SQLite, se crea automáticamente con el día de la semana correspondiente.
3. **Cálculo Determinista de Horas Decimales:**
   - Recálculo automático de `horas_decimal` a partir de las marcas provistas, empleando la función oficial `AgenteAutonomoHoras.calcular_horas_jornada`.
4. **Propagación Opcional/Inmediata hacia Google Sheets (Write-Through):**
   - Parámetro `sincronizar_sheets: bool = True`.
   - Si es `True`, dispara el volcado hacia `SPREADSHEET_ID` para ese mes/año con `forzar=True`, posicionando las marcas en las columnas exactas (C: Entrada, D/E: Almuerzo, F: Salida) y preservando la fórmula dinámica en Columna G.
5. **Esquemas Pydantic y Validaciones:**
   - Validación de formato de hora (`HH:MM` estricto en rango `00:00` a `23:59`).
   - Validación de coherencia cronológica básica (ej. `hora_salida >= hora_entrada` si ambas están presentes).

---

## 3. Fuera de Alcance (No-Scope)
- No afecta las marcaciones de materias universitarias (`asistencia_materias`).
- No afecta los movimientos financieros ni el libro contable (`LIBRO_CONTABLE_ID`).
- No permite eliminación física de jornadas (solo actualización/rectificación de horarios).

---

## 4. Matriz de Impacto e Invariantes (docs/SYSTEM_MAP.md)
- **Persistencia Local (`SYSTEM_MAP #P1`):** Mantiene la integridad de `asistencia_laboral` en `gamma_local.db`. No bloquea la base de datos y utiliza transacciones seguras.
- **Aislamiento de Hojas (`SYSTEM_MAP #S1`):** La sincronización utiliza exclusivamente `SPREADSHEET_ID`. Queda terminantemente prohibido acceder a `LIBRO_CONTABLE_ID`.
- **Compatibilidad con Reportes Existentes:** Los reportes generados por `ExcelReportService` o `preparar_datos_reporte` leerán la información rectificada tanto en SQLite como en Sheets sin discrepancias.
