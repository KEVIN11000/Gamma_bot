# Checklist de Tareas Atómicas de Implementación (Tasks) — Afinamiento del Módulo Laboral-Financiero

- **Fecha:** 27 de Octubre de 2026
- **Módulo:** Asistencia Laboral, Facturación y Reportes Financieros (`Gamma_bot`)
- **Fase SDD:** 0 (Especificación y Arquitectura)
- **Estado:** Pendiente de Aprobación en Planning Gate (Compuerta de Planificación)

---

### Tareas Atómicas de Ejecución

- [x] **Tarea 1: Implementar generador de planillas Excel nativas (`ExcelReportService`) con `openpyxl`**
  - **Archivos:** `src/services/excel_service.py`, `tests/test_excel_service.py`
  - **Acción:** Crear la clase `ExcelReportService` que construya el libro `.xlsx` respetando el diseño exacto: título de cabecera con mes y año, tabla de marcaciones diarias (A-G), formatos numéricos centrados y cuadro resumen de dos columnas (`Resumen` / `Cantidades`) con fórmulas dinámicas de suma, porcentaje e IVA, omitiendo la fila de ajuste si es 0. Añadir `openpyxl>=3.1.0` a `requirements.txt`.
  - **Criterio de Aceptación:** `pytest tests/test_excel_service.py` valida que el archivo `.xlsx` generado se abre correctamente, contiene las fórmulas esperadas y los estilos de celda.

- [ ] **Tarea 2: Refactorizar cuadro resumen y soporte de ajuste/descuento en `AgenteAutonomoHoras`**
  - **Archivos:** `src/logic/logic.py`, `tests/test_asistencia_service.py`
  - **Acción:** Actualizar `AgenteAutonomoHoras.preparar_datos_reporte` para calcular y estructurar la liquidación según el nuevo estándar: `mes`, `hora`, `por Horas`, `IVA 10%`, `INCLUIDO`, y fila opcional `SALDO ANTERIOR` / `Descuento` (solo si el monto es distinto de 0), finalizando con `FACTURA`. Agregar método `escribir_cuadro_resumen_en_sheet()` para plasmar este resumen en las celdas inferiores de la hoja activa de Google Sheets.
  - **Criterio de Aceptación:** Prueba unitaria comprobando que `preparar_datos_reporte(descuento=0)` omite la fila intermedia y que con `descuento > 0` o `ajuste > 0` calcula la factura total correcta.

- [ ] **Tarea 3: Actualizar diseño de cuadro resumen en `PDFService`**
  - **Archivos:** `src/logic/pdf_service.py`, `tests/test_services.py`
  - **Acción:** Adaptar `generar_reporte_generico` para renderizar la tabla resumen al pie con el nuevo diseño y formato monetario (`$` con separadores de miles y decimales exactos), manteniendo alineación sobria y jerarquía visual de factura final.
  - **Criterio de Aceptación:** Prueba unitaria validando generación de PDF sin excepciones y presencia de los conceptos `mes`, `hora`, `por Horas`, `IVA 10%`, `INCLUIDO`, `FACTURA`.

- [ ] **Tarea 4: Implementar motor de analíticas de asistencia laboral (Horas Perdidas, Horas Extras y MTD)**
  - **Archivos:** `src/logic/logic.py`, `tests/test_asistencia_service.py`
  - **Acción:** Crear método `calcular_analiticas_asistencia(nombre_hoja=None)` en `AgenteAutonomoHoras` que procese las jornadas con horas > 0 del período activo: calcule horas perdidas (< 8h), horas extras (> 8h), balance neto, total de horas MTD y dinero devengado acumulado.
  - **Criterio de Aceptación:** Prueba unitaria con conjunto de datos de prueba (incluyendo días < 8h, > 8h y vacíos) validando cálculos matemáticos exactos.

- [ ] **Tarea 5: Implementar función de consulta de períodos activos (Laboral y Contable)**
  - **Archivos:** `src/logic/logic.py`, `src/logic/financiero.py`, `tests/test_asistencia_service.py`
  - **Acción:** Implementar función unificada `obtener_estado_periodos()` que consulte el período laboral de `periodo_actual.txt` (con fallback de timezone paraguayo UTC-3) y el período contable en curso del `Libro_Diario` / `Cierres_Historicos`, evaluando si están sincronizados.
  - **Criterio de Aceptación:** Prueba unitaria verificando que retorna diccionario con `periodo_laboral`, `periodo_contable` y flag booleano `sincronizados`.

- [ ] **Tarea 6: Exponer endpoints REST en `api/blueprint.py` para GammaMobile**
  - **Archivos:** `src/api/blueprint.py`, `src/api/schemas.py`, `tests/test_mobile_api.py`
  - **Acción:** Declarar DTOs Pydantic y registrar los endpoints:
    - `GET /api/v1/asistencia/periodos`
    - `GET /api/v1/asistencia/analiticas`
    - `GET /api/v1/asistencia/reporte/excel` (descarga binaria de `.xlsx`)
    - `GET /api/v1/asistencia/reporte/pdf` (descarga binaria de `.pdf`)
  - **Criterio de Aceptación:** Pruebas de integración en `test_mobile_api.py` para los 4 endpoints retornando 200 OK y payloads estructurados/archivos válidos.

- [ ] **Tarea 7: Integrar comandos `/horas` y `/periodo`, y entrega dual en Telegram**
  - **Archivos:** `src/com/handlers/asistencia.py`, `src/services/asistencia_service.py`, `src/com/handlers/base.py`, `tests/test_handlers_asistencia.py`
  - **Acción:** Registrar handlers para `/horas` (resumen MTD, dinero acumulado, horas perdidas y extras) y `/periodo` (período laboral y contable). Actualizar el flujo de `/reporte` para enviar ambos archivos adjuntos (PDF y Excel `.xlsx`) al usuario.
  - **Criterio de Aceptación:** Pruebas unitarias de handlers simulando invocación de `/horas`, `/periodo` y entrega de reportes.

- [ ] **Tarea 8: Certificación de Calidad Integral, Linters y Git Clean**
  - **Archivos:** Todos los módulos modificados del proyecto.
  - **Acción:** Ejecutar `uv run pytest` sobre la suite completa de pruebas, validar `uv run flake8` y `uv run black --check` con 0 advertencias, y comprobar inmutabilidad de datos productivos.
  - **Criterio de Aceptación:** 100% de tests pasando en verde, linters limpios y working tree limpio de Git.
