# Guía Técnica de Saneamiento y Deprecación: Hoja `Obligaciones_Maestro`

**Fecha:** 2026-11-10  
**Versión de Esquema:** 17 Columnas (v2.1.2)  
**Alcance:** Libro Contable Google Sheets (`LIBRO_CONTABLE_ID`) & Repositorios de Backend (`SheetsRepository`, `AgenteFinanciero`)  

---

## 1. Contexto Histórico y Diagnóstico Columnar

La pestaña `Obligaciones_Maestro` ha evolucionado a lo largo de diversas fases del proyecto:
1. **Esquema Inicial (15 columnas):** No contaba con la columna `Tipo` y poseía una única columna genérica llamada `Cuotas`.
2. **Esquema Intermedio (16 columnas):** Se incorporó la columna `Tipo` en la posición B (índice 2) y se desglosaron `Cuotas_Totales` y `Cuotas_Restantes`. Sin embargo, para evitar corrimientos destructivos en hojas de usuarios activos, se preservó la columna original `Cuotas` y la columna `Event_ID`.
3. **Esquema v2.1 (17 columnas):** Se incorporó la columna `Es_Gasto_Fijo` (columna Q / índice 17) para desacoplar el Margen Libre Disponible (MLD) de las deudas pausadas.

---

## 2. Inventario y Dictamen de las 17 Columnas

| Pos. | Columna | Nombre de Campo | Tipo de Dato | Estado Operativo | Justificación y Tratamiento |
|:---:|:---:|---|---|:---:|---|
| 1 | A | `ID_Obligacion` | `str` (alfanumérico) | **ACTIVO (Clave)** | Clave primaria única del registro (`OBL-...`, `PRY-...`). |
| 2 | B | `Tipo` | `str` | **ACTIVO** | "Deuda", "Prestamo", "Tarjeta", "Credito", "Proyecto". |
| 3 | C | `Nombre` | `str` | **ACTIVO** | Denominación descriptiva del crédito. |
| 4 | D | `Entidad` | `str` | **ACTIVO** | Acreedor o entidad financiera (Banco, Cooperativa). |
| 5 | E | `Monto_Inicial` | `int` (Gs.) | **ACTIVO** | Capital inicial financiado. |
| 6 | F | `Saldo_Actual` | `int` (Gs.) | **ACTIVO** | Capital vivo remanente (se reduce con cada abono). |
| 7 | G | `Estado` | `str` | **ACTIVO** | "Activo", "Pausado", "Pagado", "Cancelado", "Simulado". |
| 8 | H | `Cuota_Referencia_Gs`| `int` (Gs.) | **ACTIVO** | Importe monetario mensual a pagar. |
| 9 | I | `Fecha_Inicio` | `str` (`YYYY-MM-DD`) | **ACTIVO** | Fecha de inicio del compromiso. |
| 10 | J | `Observaciones` | `str` | **ACTIVO** | Notas adicionales o rastro de abonos. |
| 11 | K | **`Cuotas`** | `int` / `str` | ⚠️ **DEPRECATED (Legacy)** | **Redundante con `Cuotas_Totales` (Columna N).** Se preserva físicamente en la planilla para no romper fórmulas de usuario. En inserciones, el backend autocompleta defensivamente `Cuotas = Cuotas_Totales`. En lecturas, se prioriza `Cuotas_Restantes` y `Cuotas_Totales`. Omitido en la API móvil. |
| 12 | L | **`Event_ID`** | `str` | ⚠️ **DEPRECATED (Inactivo)** | **Vestigio de Google Calendar.** Casi todas las altas guardan `""`. El timeline moderno se calcula determinísticamente con `Dia_Vencimiento`. Se preserva físicamente con valor por defecto `""`. Omitido en la API móvil. |
| 13 | M | `Dia_Vencimiento` | `int` (1..31) | **ACTIVO** | Día del mes en que vence la cuota. Crucial para Cashflow. |
| 14 | N | `Cuotas_Totales` | `int` | **ACTIVO** | Cantidad total de cuotas acordadas. |
| 15 | O | `Cuotas_Restantes` | `int` | **ACTIVO** | Cuotas pendientes a amortizar (decrementa en abonos). |
| 16 | P | `Orden_Prioridad` | `int` | **ACTIVO** | Prioridad para estrategia Avalancha (1 = liquidar primero). |
| 17 | Q | `Es_Gasto_Fijo` | `int` (1 o 0) | **ACTIVO (v2.1)** | Define si la cuota resta del MLD. Al pausar conmuta a 0. |

---

## 3. Reglas de Invarianza y Compatibilidad

1. **Invariante de Integridad Columnar:**  
   Bajo ninguna circunstancia se deben eliminar físicamente las columnas K (`Cuotas`) y L (`Event_ID`) de hojas de cálculo de producción sin un script formal de migración, ya que provocaría el corrimiento de `Dia_Vencimiento` a la columna K y de `Es_Gasto_Fijo` a la columna O.
2. **Desacoplamiento de Clientes:**  
   Las aplicaciones cliente (Gamma Mobile y webhooks) solo consumen y envían `cuotas_totales`, `cuotas_restantes`, `dia_vencimiento` y `cuota_referencia_gs`. El backend asume la responsabilidad de alimentar defensivamente las columnas legadas.
