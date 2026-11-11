# Especificación Funcional: Endpoint de Capacidades y Optimización de Reportes A4 (v2.1.4)

## 1. Resumen Ejecutivo
Este ciclo introduce dos capacidades prioritarias para el ecosistema Gamma:
1. **Endpoint de Auto-Descubrimiento de la API (`GET /api/v1/capacidades`)**: Permite a Gamma Mobile y a cualquier cliente consultar dinámicamente el catálogo completo de rutas activas, métodos HTTP, módulos, descripciones y flags de capacidades de alto nivel, posibilitando feature toggles dinámicos sin desbordes ni fallos por versiones no coincidentes.
2. **Calibración Dimensional de Reportes PDF en ReportLab (Hoja Única A4)**: Ajusta la geometría, banner de título, tipografía y paddings verticales para certificar empíricamente que un mes calendario completo de hasta 31 días corridos más el cuadro resumen de facturación con IVA encaje al 100% en una sola hoja A4 (92.4% ocupación, 2.1 cm de margen libre).
3. **Estandarización Canónica de Liquidación Laboral**: Unificación de etiquetas en backend, PDF y Excel (`Horas del mes`, `Monto por hora`, `Total Monto por Horas`, `IVA 10%`, `TOTAL IVA INCLUIDO`, y ajuste opcional de `SALDO ANTERIOR` / `Descuento`).

---

## 2. Casos de Uso y Alcance

### CU-1: Consulta Dinámica de Capacidades de la API
* **Actor:** Gamma Mobile / Desarrollador / Consumidor REST.
* **Flujo Principal:**
  1. El cliente realiza una petición `GET /api/v1/capacidades` (con cabecera `X-API-KEY` o token válido).
  2. El servidor inspecciona dinámicamente `current_app.url_map` en memoria, filtrando todas las rutas correspondientes a `/api/v1`.
  3. El servidor categoriza cada endpoint según su módulo funcional (`presupuesto`, `obligaciones`, `asistencia`, `movimientos`, `cierres`, `reportes`, etc.).
  4. El servidor extrae métodos HTTP disponibles, docstring descriptivo y estatus de autenticación requerida.
  5. El servidor inyecta la versión del backend (`VERSION`), conteo total de rutas y mapa de capacidades booleanas.
  6. El servidor retorna un JSON HTTP 200 con la estructura canónica.
* **Filtros Opcionales:**
  - `?modulo=<nombre>`: Filtra y retorna únicamente las rutas pertenecientes al módulo especificado (ej. `?modulo=presupuesto`).

### CU-2: Generación de Reporte PDF Laboral en Hoja Única A4
* **Actor:** Usuario final (vía Telegram `/reporte`, WhatsApp o Gamma Mobile `GET /api/v1/asistencia/reporte/pdf`).
* **Flujo Principal:**
  1. El usuario solicita la liquidación de horas del período (hasta 31 días calendario).
  2. El motor `PDFService` aplica la geometría calibrada de hoja A4:
     - Márgenes uniformes de 1.0 cm (785.20 pt de alto útil).
     - Banner A1:G1 unificado de 20 pt de alto.
     - Subtítulo + metadata de fecha de emisión (16 pt).
     - Grilla diaria de 7 columnas (`Día`, `Fecha`, `Hora entrada`, `Salgo almuerzo`, `Vuelta almuerzo`, `Hora salida`, `Horas`) con padding vertical de 2.2 pt.
     - Cuadro resumen inferior con formato de factura impositiva (`Horas del mes`, `Monto por hora`, `Total Monto por Horas`, `IVA 10%`, `TOTAL IVA INCLUIDO`, y fila de ajuste si aplica).
  3. El documento se compila en memoria o disco asegurando que el total de páginas sea exactamente 1.

### CU-3: Estandarización de Etiquetas en Planilla Excel (.xlsx) y Google Sheets
* **Actor:** Usuario final (vía Telegram, bot o API `GET /api/v1/asistencia/reporte/excel`).
* **Flujo Principal:**
  1. El servicio `ExcelReportService` y el método `escribir_cuadro_resumen_en_sheet` generan el cuadro resumen con las etiquetas de negocio explícitas y legibles, manteniendo fórmulas dinámicas vivas (`=SUM(...)`, `=ROUND(...)`).

---

## 3. Lo que Queda Fuera de Alcance (No-Scope)
- No se eliminan ni alteran columnas preexistentes en la planilla de Google Sheets.
- No se modifican los contratos de cálculo matemático (las fórmulas de IVA 10% y redondeos se mantienen idénticas).
- No se expondrán endpoints internos de soporte o testing (`/debug`, `/_internal`) dentro del catálogo de capacidades públicas.

---

## 4. Matriz de Impacto e Invariantes del Sistema (`docs/SYSTEM_MAP.md`)

| Invariante | Descripción | Impacto y Salvaguarda |
| :--- | :--- | :--- |
| **INV-F1** | Integridad de 17 columnas de `Obligaciones_Maestro` | **Neutro**: No se modifica la persistencia de obligaciones. |
| **INV-F2** | Aislamiento de MLD frente a gastos de Libro Diario | **Neutro**: No se alteran fórmulas del Margen Libre Disponible. |
| **INV-F5** | Preservación de formato monetario guaraníes / dólares | **Protegido**: Formateo de moneda y comas decimales se preservan idénticos. |
| **INV-P1** | Preservación de registros locales frente a Sheets | **Protegido**: Cero impacto en sincronización bidireccional. |
| **INV-A4** | Certificación de Hoja Única A4 en reportes laborales | **Nuevo Invariante**: Todo reporte mensual de horas (hasta 31 días) debe compilar en 1 sola página. |
