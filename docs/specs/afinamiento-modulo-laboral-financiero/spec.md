# Especificación Funcional (Spec) — Afinamiento del Módulo Laboral-Financiero
## Generación Dual Excel/PDF, Cuadro Resumen Contable, Analíticas de Déficit de Horas y Consulta de Períodos

- **Fecha:** 27 de Octubre de 2026
- **Módulo:** Asistencia Laboral, Facturación y Reportes Financieros (`Gamma_bot`)
- **Fase SDD:** 0 (Especificación y Arquitectura)
- **Estado:** Listo para revisión de planificación (Planning Gate)

---

## 1. Alcance y Objetivos

Evolucionar el módulo de asistencia y horas de `Gamma_bot` para automatizar por completo la confección de la planilla de cobro laboral exactamente bajo el estándar requerido para la rendición de haberes, eliminando la necesidad de edición manual posterior:
1. **Cuadro Resumen Estandarizado:** Estructurar la tabla de liquidación al pie de la planilla con: Total de horas del mes (`mes`), Tarifa horaria (`hora`), Monto total multiplicado (`por Horas`), IVA 10% calculado, Subtotal con IVA (`INCLUIDO`), Ajuste extraordinario o Descuento opcional (`SALDO ANTERIOR` / `Descuento`, omitiendo la fila si el monto es cero), y Total a facturar (`FACTURA`).
2. **Generación Dual de Documentos:** Generar y entregar tanto la planilla de cálculo en formato Excel nativo (`.xlsx` con estilos, cuadrícula y fórmulas matemáticas activas) como el comprobante digital en formato PDF (ReportLab), además de reflejar el cuadro resumen al pie de la hoja en Google Sheets.
3. **Motor de Analíticas Laborales MTD:** Computar el acumulado a la fecha (horas trabajadas y dinero devengado en el período en curso), junto con la métrica de horas perdidas (déficit acumulado respecto a la jornada estándar de 8 horas en días efectivamente trabajados) y horas extras acumuladas (> 8h).
4. **Consulta Unificada de Períodos:** Exponer en qué período activo se encuentra el sistema de marcación laboral (`periodo_actual.txt` / Google Sheets) y el sistema contable (`Libro_Diario` / `Cierres_Historicos`).
5. **Acceso Multi-Canal:** Habilitar la interacción completa mediante comandos directos e interactivos en Telegram (`/horas`, `/periodo`, `/reporte`) y mediante endpoints REST protegidos en `/api/v1/asistencia/` para la aplicación móvil `GammaMobile`.

---

## 2. Casos de Uso del Alcance (Scope)

### UC-1: Cuadro Resumen Laboral en Planilla y Reportes
- **Actor:** Usuario / Administrador.
- **Flujo:**
  1. El sistema lee las marcaciones de la hoja del período activo (columnas: *Día*, *Fecha*, *Hora entrada*, *Salgo almuerzo*, *Vuelta almuerzo*, *Hora salida*, *Horas*).
  2. Totaliza las horas trabajadas en valor decimal (ej. `107.3`).
  3. Recupera el monto por hora configurado (`MONTO_POR_HORA`, default `$14,634`).
  4. Calcula `por Horas = mes * hora` (ej. `$1,569,984`).
  5. Calcula `IVA 10% = por Horas * 0.10` (ej. `$156,998`).
  6. Calcula `INCLUIDO = por Horas + IVA 10%` (ej. `$1,726,983`).
  7. **Condición de Ajuste / Descuento:**
     - Si se especifica un monto adicional a favor (deuda previa o reintegro), se incluye la fila `SALDO ANTERIOR` sumando al total.
     - Si se especifica un descuento (adelanto o deducción), se incluye la fila `Descuento` restando al total.
     - **Si el valor es 0 o no se suministra, la fila se omite completamente** tanto en Excel como en PDF y Google Sheets.
  8. Totaliza `FACTURA`:
     - Sin ajuste/descuento: `FACTURA = INCLUIDO`.
     - Con ajuste: `FACTURA = INCLUIDO + SALDO ANTERIOR`.
     - Con descuento: `FACTURA = INCLUIDO - Descuento`.

### UC-2: Generación y Entrega Dual (.xlsx y .pdf)
- **Actor:** Usuario de Telegram / Cliente Móvil GammaMobile.
- **Flujo:**
  1. Al solicitar el reporte del período (o al ejecutar el cierre mensual laboral), el backend compila dos artefactos:
     - Archivo Excel `.xlsx` generado con `openpyxl`, con encabezados estilizados, bordes, formatos de celda (horas en decimal y moneda con `$`), y fórmulas dinámicas de suma e IVA.
     - Archivo PDF generado con `reportlab`, con la tabla de registros y el cuadro resumen idéntico.
  2. En Telegram, el bot entrega ambos documentos adjuntos en el chat.
  3. En la API REST, se habilitan endpoints de descarga directa para ambos tipos de archivo.

### UC-3: Persistencia y Actualización en Google Sheets
- **Actor:** Sistema / AgenteAutonomoHoras.
- **Flujo:**
  1. Tras consolidar las filas de marcación del mes, el backend escribe al pie de la hoja activa (dejando una fila en blanco) la tabla de dos columnas: `Resumen` y `Cantidades`.
  2. Escribe las etiquetas y valores (`mes`, `hora`, `por Horas`, `IVA 10%`, `INCLUIDO`, ajuste/descuento si aplica, y `FACTURA`).

### UC-4: Analíticas de Horas y Rendimiento MTD
- **Actor:** Usuario de Telegram / GammaMobile.
- **Flujo:**
  1. El usuario invoca `/horas` o consulta `GET /api/v1/asistencia/analiticas`.
  2. El sistema analiza los registros del período activo hasta la fecha:
     - **Días con marcación:** Días con horas computadas > 0.
     - **Horas Perdidas:** Suma del déficit exclusivamente en días donde se trabajó menos de 8h:
       $$\text{Horas Perdidas} = \sum_{d \in \text{días trabajados}} \max(0, 8.0 - h_d)$$
     - **Horas Extras:** Suma de las horas excedentes en días donde se trabajó más de 8h:
       $$\text{Horas Extras} = \sum_{d \in \text{días trabajados}} \max(0, h_d - 8.0)$$
     - **Balance Neto:** $\text{Total Horas Trabajadas} - (\text{Días Trabajados} \times 8.0)$.
     - **Total Horas Trabajadas MTD.**
     - **Dinero Devengado MTD:** $\text{Total Horas MTD} \times \text{Monto por Hora}$.
  3. Emite un informe estructurado con formato visual limpio.

### UC-5: Consulta de Períodos Activos
- **Actor:** Usuario de Telegram / GammaMobile.
- **Flujo:**
  1. El usuario invoca `/periodo` o consulta `GET /api/v1/asistencia/periodos`.
  2. El backend inspecciona:
     - Período Laboral actual (leído de `periodo_actual.txt` con fallback al mes calendario vigente en zona horaria UTC-3).
     - Período Contable actual (mes y año en curso del `Libro_Diario` y último cierre en `Cierres_Historicos`).
  3. Retorna el estado sincronizado de ambos subsistemas indicando si están alineados.

---

## 3. Lo que queda Excluido (No-Scope)

- No se modificará la estructura de columnas A-G de las marcaciones diarias en Google Sheets para no romper compatibilidad histórica.
- No se alterarán los horarios ni la lógica de materias de docencia en `AgenteAsistenciaMaterias`.
- No se incluirán días sin marcación como días perdidos (los días libres/feriados no penalizan el cálculo de horas perdidas).
- Los cambios en la interfaz gráfica de Android en `GammaMobile` corresponden a su workspace móvil; en `Gamma_bot` se entrega la totalidad de contratos, endpoints y lógica de backend.

---

## 4. Criterios de Aceptación Verificables

1. **Formato de Resumen:** La tabla de resumen generada en Excel y PDF contiene exactamente los campos `mes`, `hora`, `por Horas`, `IVA 10%`, `INCLUIDO`, y `FACTURA`. Si `ajuste/descuento == 0`, no existe ninguna fila intermedia de deducción/ajuste. Si `ajuste != 0`, se muestra la fila correspondiente sumando o restando según el tipo.
2. **Generación Excel (.xlsx):** El archivo `.xlsx` se genera correctamente, es parseable por `openpyxl`, contiene el título del mes, la cuadrícula de días con horas y la tabla resumen al pie.
3. **Generación PDF:** El PDF de horas refleja exactamente la misma tabla y totales que el archivo Excel.
4. **Cálculo de Analíticas:** Dado un período con jornadas de 7.43h, 7.92h y 8.45h:
   - Horas trabajadas = 23.8h.
   - Horas perdidas = $(8 - 7.43) + (8 - 7.92) = 0.57 + 0.08 = 0.65\text{h}$.
   - Horas extras = $8.45 - 8 = 0.45\text{h}$.
   - Balance neto = $-0.20\text{h}$.
5. **Endpoints REST:**
   - `GET /api/v1/asistencia/periodos` responde HTTP 200 con `{ "periodo_laboral": "...", "periodo_contable": "..." }`.
   - `GET /api/v1/asistencia/analiticas` responde HTTP 200 con métricas MTD y desglose de horas.
   - `GET /api/v1/asistencia/reporte/excel` descarga binaria de archivo `.xlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).
6. **Comandos de Telegram:**
   - `/horas` responde con el resumen MTD, dinero devengado, horas perdidas y balance.
   - `/periodo` responde con el estado de ambos períodos.
   - `/reporte` entrega tanto el archivo `.pdf` como el archivo `.xlsx`.
7. **Regresión:** La suite completa de 202 tests existentes sigue pasando al 100% y linters (`flake8`, `black --check`) limpios.
