# Especificación Funcional (Spec): Paridad Financiera, Acceso a Presupuesto y Saneamiento de Obligaciones Maestro

**Feature:** `paridad-presupuesto-obligaciones-mobile`  
**Fecha:** 2026-11-10  
**Fase SDD:** 0 — Especificación y Arquitectura (Modo Planificador)  
**Estado:** Propuesta de Planificación  

---

## 1. Contexto y Diagnóstico de Inquietudes del Usuario

A partir de la experiencia operativa del usuario y la auditoría exhaustiva del sistema, se identificaron tres brechas funcionales y arquitectónicas:

1. **Aislamiento de la Hoja de Presupuesto en la App Móvil (`GammaMobile`):**
   - Actualmente, en la planilla contable existe la pestaña `Presupuesto_Base` (con el salario base, gastos fijos por categoría y techos presupuestarios).
   - Sin embargo, en la app móvil no existe ninguna pantalla ni flujo de lectura ni de escritura para esta hoja. El usuario está forzado a ingresar a Google Sheets o usar comandos en Telegram (`/fijos`, `/fijo_set`, `/fijo_nuevo`).
   - En el backend existen endpoints parciales (`GET /presupuesto/fijos`, `PUT /presupuesto/fijos/{concepto}`, `POST /presupuesto/fijos`, `PUT /presupuesto/salario-base`, `GET /presupuesto/techos`), pero faltan capacidades esenciales como la eliminación de un gasto fijo (`DELETE`) y la configuración directa de techos de consumo variable (`PUT /presupuesto/techos/{categoria}`).

2. **Columnas Redundantes y Obsoletas en `Obligaciones_Maestro`:**
   - La hoja `Obligaciones_Maestro` cuenta actualmente con 17 columnas.
   - La auditoría técnica detectó dos columnas con problemas de redundancia y obsolescencia:
     - **`Cuotas` (Columna 11 / K):** Columna *legacy* previa a la separación entre `Cuotas_Totales` (Columna 14 / N) y `Cuotas_Restantes` (Columna 15 / O). Al dar de alta una deuda se duplica el valor de `Cuotas_Totales` en `Cuotas`. Históricamente generó confusión al ser interpretada en algunos scripts como monto de cuota y en otros como cantidad de cuotas.
     - **`Event_ID` (Columna 12 / L):** Originalmente concebida para almacenar el ID de eventos en Google Calendar. En la práctica, casi la totalidad de las altas vía REST y móviles guardan una cadena vacía `""`. El timeline de vencimientos moderno del sistema se calcula matemáticamente mediante `Dia_Vencimiento` sin requerir Google Calendar.

3. **Paridad de Métodos Bot ↔ App Móvil:**
   - El bot de Telegram cuenta con potentes comandos financieros interactivos (`/deudas`, `/nueva_deuda`, `/abonar`, `/foco`, `/estrategia`, `/vencimientos`, `/evaluar_abono`, `/simular`, `/aprobar_proyecto`, `/cierre_mensual`) que deben estar disponibles de forma nativa y visual en la app móvil `GammaMobile` a través de contratos REST formales.

---

## 2. Alcance (In-Scope)

### 2.1 Módulo Presupuesto (Lectura y Escritura en Gamma Mobile)
1. **Contratos Backend para Presupuesto Integral:**
   - Incorporación de `DELETE /api/v1/presupuesto/fijos/<concepto>` para permitir eliminar conceptos fijos que ya no aplican.
   - Incorporación de `PUT /api/v1/presupuesto/techos/<categoria>` para permitir fijar o editar el límite de gasto mensual de categorías variables (Supermercado, Combustible, etc.) directamente desde la app.
   - Mantener y robustecer `GET /presupuesto/fijos`, `POST /presupuesto/fijos`, `PUT /presupuesto/fijos/<concepto>`, `PUT /presupuesto/salario-base` y `GET /presupuesto/techos`.
2. **Especificación UI para Gamma Mobile (`PresupuestoScreen`):**
   - Tarjeta superior con **Salario Base** editable (diálogo interactivo de actualización).
   - Métricas de resumen: Total Gastos Fijos vs. Margen Libre Proyectado.
   - Lista colapsable por categorías de **Gastos Fijos** con botón de edición rápida de monto, botón de eliminación y FAB/Botón para "Agregar Gasto Fijo".
   - Sección de **Techos Presupuestarios Variables** con barras de progreso de consumo en tiempo real (indicador Normal, Alerta 80%, Excedido 100%) y selector para ajustar el techo mensual.

### 2.2 Saneamiento y Deprecación Segura de `Obligaciones_Maestro`
1. **Dictamen Técnico de Columnas:**
   - Mantener las 17 columnas físicas en Google Sheets para garantizar estricta compatibilidad hacia atrás con registros históricos y evitar quebrar fórmulas externas.
   - Establecer `Cuotas` y `Event_ID` como **Campos Obsoletos en Fase de Deprecación (Legacy/Ignored)**.
   - En el backend, garantizar que la lectura y escritura se basen exclusivamente en `Cuotas_Totales`, `Cuotas_Restantes`, `Cuota_Referencia_Gs` y `Dia_Vencimiento`.
   - Si se inserta una nueva obligación, el backend completa defensivamente `Cuotas = Cuotas_Totales` y `Event_ID = ""` sin exigir estos campos en los DTOs de Gamma Mobile.
   - Documentar la guía de limpieza columnar en la planilla maestra.

### 2.3 Paridad Funcional de Comandos del Bot hacia Gamma Mobile
Reflejar en especificaciones de UI/UX y contratos REST las siguientes capacidades del bot:
1. **Abono de Obligaciones (`/abonar`):**
   - Modal/Pantalla en `ObligacionesScreen` para ingresar monto de abono, actualizar saldo y cuotas restantes, y generar automáticamente el asiento en `Libro_Diario` (`POST /api/v1/obligaciones/abonar`).
2. **Deuda Foco y Estrategias (`/foco`, `/estrategia`):**
   - Selector en la app móvil entre **Avalancha** (mayor costo) y **Bola de Nieve** (menor saldo).
   - Card destacada en el tope de `ObligacionesScreen` con la **Deuda Foco** recomendada (`GET /api/v1/obligaciones/foco`).
3. **Timeline de Vencimientos (`/vencimientos`):**
   - Vista de agenda cronológica mensual en la app móvil alimentada por `GET /api/v1/obligaciones/vencimientos`.
4. **Simulador y Aprobador de Proyectos (`/simular`, `/aprobar_proyecto`):**
   - Formulario de simulación What-If que evalúa impacto en el MLD y ratio DTI, con semáforo visual (Verde, Amarillo, Rojo) y botón para aprobar y activar el crédito.

---

## 3. Fuera de Alcance (No-Scope)

- Modificación destructiva de las columnas en la hoja Google Sheets en producción sin script de migración auditado.
- Alteraciones a la lógica laboral o de asistencia (el foco es estrictamente presupuestario y financiero).
- Eliminación de comandos existentes en el Bot de Telegram (se preserva la omnicanalidad 1:1).

---

## 4. Matriz de Impacto e Invariantes de Gobernanza (vs. `docs/SYSTEM_MAP.md`)

| Invariante | Impacto Evaluado | Mitigación / Salvaguarda |
|---|---|---|
| **INV-F1** (Aislamiento de Hojas) | Neutro | Todas las operaciones presupuestarias operan sobre `LIBRO_CONTABLE_ID`, sin interactuar con planillas de asistencia. |
| **INV-F2** (Invarianza del MLD) | Positivo | Al permitir editar gastos fijos y pausar deudas desde la app, el cálculo de MLD se actualiza reactivamente sin verse contaminado por gastos diarios. |
| **INV-F3** (Asiento Unificado en Abonos) | Alto | La pantalla de abonos móviles consumirá estrictamente `POST /api/v1/obligaciones/abonar`, que garantiza el asiento atómico en `Libro_Diario`. |
| **INV-F5** (Cooldown Anti-Spam 24h) | Neutro | Las alertas de techos continuarán aplicando el cooldown de 24h por categoría ante cualquier gasto registrado desde la app. |
