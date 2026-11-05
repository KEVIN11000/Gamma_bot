# Feature Specification: Paridad Funcional Backend API v2 para Gamma Mobile (Fase 6)

**Feature Branch:** `Main-stable`  
**Created:** 2026-11-04  
**Status:** Planificación (Fase 0 - SDD)  
**Input:** Requerimientos de adecuación y paridad total entre el Core Bot de Telegram y la API REST (`/api/v1/`) consumida por la app Android `GammaMobile`.

---

## 1. Alcance y Contexto del Negocio

El backend de `Gamma_bot` dispone de motores avanzados para la gestión financiera, control de costos fijos, simulación de capacidad crediticia, techos presupuestarios preventivos y control de horas laborales. Sin embargo, la versión previa de la API REST expuesta para la app móvil carecía de endpoints clave que el bot ejecuta habitualmente mediante comandos interactivos.

La **Fase 6** tiene como objetivo implementar los endpoints REST faltantes en `/api/v1/`, completando la paridad operativa al 100% con los siguientes pilares:

1. **Gestión de Presupuesto Base y Gastos Fijos (`Presupuesto_Base`):**
   - Lectura integral de ingresos de referencia y costos fijos por categoría (`GET /api/v1/presupuesto/fijos`).
   - Actualización del monto de un costo fijo existente (`PUT /api/v1/presupuesto/fijos/{concepto}`).
   - Registro de nuevos conceptos de gasto fijo (`POST /api/v1/presupuesto/fijos`).
   - Actualización del sueldo o ingreso base mensual (`PUT /api/v1/presupuesto/salario-base`).
   - Monitoreo consolidado de techos presupuestarios variables por categoría (`GET /api/v1/presupuesto/techos`).
2. **Ciclo de Vida de Proyectos de Inversión y Capital:**
   - Simulación estructurada de proyectos con cálculo de Margen Libre (MLD), Endeudamiento Global (DTI), semáforo y guardado en estado `"Simulado"` con ID persistente (`POST /api/v1/proyectos/simular`).
   - Aprobación formal de proyectos con transición a estado `"Activo"` en la hoja de obligaciones (`POST /api/v1/proyectos/{id_proyecto}/aprobar`).
3. **Estado de Jornada Laboral en Tiempo Real:**
   - Consulta rápida y no mutativa del estado del día para la pantalla principal de Android (`GET /api/v1/asistencia/estado-hoy`). Permite saber al instante si el usuario ya marcó entrada, hora de inicio, tiempo laborado transcurrido y si puede marcar salida.
4. **Reportes Descargables del Libro Diario:**
   - Descarga autenticada de balances y transacciones del Libro Diario en formato Excel (`GET /api/v1/reportes/financiero/excel`) y PDF (`GET /api/v1/reportes/financiero/pdf`).
5. **Hidratación Global Atómica (Bootstrap):**
   - Agregador de inicio rápido (`GET /api/v1/bootstrap`) que consolida resumen financiero, estado de jornada de hoy, pronóstico del clima y próximos compromisos en una sola petición HTTP.

---

## 2. Casos de Uso y Escenarios de Aceptación

### Caso de Uso 1: Consulta y Edición de Gastos Fijos (P1)
- **Actor:** App móvil Gamma Mobile en la sección "Presupuesto".
- **Flujo:**
  1. La app llama a `GET /api/v1/presupuesto/fijos`.
  2. Recibe el salario base, total acumulado de fijos y el mapa de categorías con sus conceptos y montos.
  3. El usuario modifica el monto de "Alquiler" y la app envía `PUT /api/v1/presupuesto/fijos/Alquiler` con `{"nuevo_monto": 1600000}`.
- **Criterio de Aceptación:** Google Sheets actualiza la celda correspondiente mediante `SheetsRepository.actualizar_monto_gasto_fijo` y la caché se invalida inmediatamente.

### Caso de Uso 2: Monitoreo de Techos Presupuestarios Variables (P1)
- **Actor:** Dashboard móvil al cargar tarjetas de progreso financiero.
- **Flujo:** Llama a `GET /api/v1/presupuesto/techos`.
- **Criterio de Aceptación:** Devuelve para cada categoría activa su límite presupuestado, gasto devengado en el mes, porcentaje de consumo, umbral configurado (ej. 80%) y estado (`"NORMAL"` o `"ALERTA"`).

### Caso de Uso 3: Simulación y Aprobación de Proyecto de Gasto/Inversión (P1)
- **Actor:** Usuario evaluando adquirir un equipamiento en cuotas.
- **Flujo:**
  1. Envía `POST /api/v1/proyectos/simular` con `{"concepto": "Notebook", "monto": 6000000, "meses": 12}`.
  2. Recibe `id_proyecto: "PRY-XXXX"`, cuota de 500.000 ₲, nuevo MLD, DTI y semáforo.
  3. El usuario presiona "Aprobar Proyecto" en la app, enviando `POST /api/v1/proyectos/PRY-XXXX/aprobar`.
- **Criterio de Aceptación:** El registro en `Obligaciones_Maestro` pasa de `"Simulado"` a `"Activo"` con código HTTP 200 OK.

### Caso de Uso 4: Consulta de Estado Diario de Asistencia (P1)
- **Actor:** Pantalla de Inicio / Reloj de Gamma Mobile al abrir la aplicación.
- **Flujo:** Llama a `GET /api/v1/asistencia/estado-hoy`.
- **Criterio de Aceptación:** Si hoy ya se marcó entrada a las 08:02 y no hay salida, devuelve `estado: "TRABAJANDO"`, `puede_marcar_entrada: false`, `puede_marcar_salida: true` y minutos transcurridos computados contra la hora local de Paraguay.

### Caso de Uso 5: Descarga de Reportes Financieros Libro Diario (P2)
- **Actor:** Usuario solicitando reporte contable del mes.
- **Flujo:** Llama a `GET /api/v1/reportes/financiero/excel?mes=11&anio=2026` con `X-API-KEY`.
- **Criterio de Aceptación:** Retorna el archivo binario `.xlsx` con encabezados `Content-Disposition: attachment`.

### Caso de Uso 6: Inicio Ultrarrápido de la App con Bootstrap (P2)
- **Actor:** Gamma Mobile durante el splash/inicio.
- **Flujo:** Llama a `GET /api/v1/bootstrap`.
- **Criterio de Aceptación:** Retorna en una sola llamada los bloques de resumen financiero, estado laboral de hoy, clima y avisos urgentes en <300ms.

---

## 3. Lo que queda Excluido (No-Scope)
- ❌ Modificación del esquema de base de datos de Google Sheets existente (`Presupuesto_Base` y `Obligaciones_Maestro` mantienen sus columnas canónicas).
- ❌ Alteración de la autenticación o bypass del decorador `@require_api_key`.
- ❌ Creación de pasarelas de pago o débitos bancarios automáticos.
