# ESPECIFICACIÓN DE REQUERIMIENTOS: CORE BACKEND V2.0.0 (FASE 1)
**Feature:** `core-backend-v2-fase1`  
**Versión de Salto:** v2.0.0  
**Fecha:** 2 de Noviembre de 2026  
**Estado:** Propuesta de Planificación (Fase 0 - SDD)  
**Perfil de Usuario:** Profesional que trabaja y estudia en la universidad (estudiante-trabajador).  
**Restricción de Infraestructura:** PythonAnywhere con 1 worker WSGI (presupuesto controlado, cero tolerancia a bloqueos síncronos).

---

## 1. OBJETIVO GENERAL
Evolucionar la arquitectura de `Gamma_bot` hacia la versión **v2.0.0**, transformándolo en un **Core Backend desacoplado y omnicanal** capaz de atender fluidamente a clientes móviles (Gamma Mobile), bots conversacionales (Telegram y futuro WhatsApp) y aplicaciones web, bajo una política de **Persistencia Local Primaria (Local-First)** y eliminación completa del acoplamiento por scraping de texto entre componentes.

---

## 2. CASOS DE USO Y ALCANCE FUNCIONAL

### 2.1. Dominio Laboral (Estudiante que Trabaja)
- **CU-LAB-01: Marcación Rápida Desacoplada (Entrada/Salida)**
  - El usuario puede marcar jornada laboral desde el bot de Telegram o desde la API móvil.
  - La operación debe registrarse **inmediatamente (< 10ms) en la base de datos relacional local del servidor** como fuente primaria de verdad.
  - El resultado devuelto por el dominio debe ser un DTO tipado (`MarcacionResult`).
  - El reflejo hacia Google Sheets debe realizarse de forma asíncrona/desacoplada para no retener el único worker WSGI de PythonAnywhere.
- **CU-LAB-02: Corte Automático de Salida por Configuración**
  - Existencia de un parámetro configurable de fin de jornada (`HORA_SALIDA_DEFECTO`, por defecto `17:00`).
  - Durante la ejecución del ciclo de mantenimiento/cron (aprovechando latidos existentes), si una jornada del día tiene "Entrada" pero carece de "Salida" habiendo superado el horario configurado, el sistema ejecuta el corte automático o asienta la salida por defecto para evitar jornadas abiertas y horas no computadas.
- **CU-LAB-03: Sincronización y Volcado Bidireccional (DB <-> Sheets)**
  - Opción/endpoint para volcar registros locales de asistencia hacia la hoja de cálculo de Google Sheets.
  - Opción/endpoint para importar o reconciliar desde Google Sheets hacia la DB local si el usuario corrigió manualmente alguna celda en la nube.

### 2.2. Dominio Académico (Estudiante Universitario)
- **CU-ACA-01: Marcación de Asistencia a Cátedra**
  - Registro de asistencia a la materia universitaria que el usuario está cursando en ese horario.
  - Almacenamiento primario en la base de datos local y reflejo en la planilla de materias.
  - Excluido explícitamente: liquidación de honorarios docentes o cálculo de horas cátedra (el usuario es estudiante, no docente).
- **CU-ACA-02: Integración de Calendario Lectivo**
  - Prevención de alertas o bloqueos durante feriados y recesos universitarios declarados.

### 2.3. Dominio Financiero (Gestión Estratégica)
- **CU-FIN-01: Unificación de Lógica de Deudas y Abonos**
  - Centralizar en `src/logic/financiero.py` una única fuente de verdad para el alta de obligaciones y el registro de abonos.
  - Ambos canales (Telegram y Mobile API) deben imputar contablemente con la misma nomenclatura exacta (`Categoría = "Préstamos / Deudas"`, generación homogénea de asientos en `Libro_Diario` y actualización de cuotas).
- **CU-FIN-02: Techos Presupuestarios Variables Configurables**
  - Soporte de límites presupuestarios por categoría de gasto variable en `Presupuesto_Base` (ej. Ocio, Gastos Varios).
  - Configurable y con interruptor de encendido/apagado (*feature toggle*).
  - Alerta preventiva cuando el gasto acumulado mensual alcance un umbral parametrizable (por defecto 80%).

### 2.4. Dominio Logístico y Experiencia Móvil
- **CU-LOG-01: Endpoint REST de Clima para Gamma Mobile**
  - Exponer `GET /api/v1/clima` reutilizando la consulta a Open-Meteo (`src/logic/cron_jobs.py`), retornando temperatura actual, máxima/mínima, probabilidad de lluvia y recomendación de paraguas en JSON estructurado para alimentar el dashboard móvil.

---

## 3. MODULARIZACIÓN DEL MONOLITO REST (`src/api/blueprint.py`)

El archivo actual de 2.451 líneas se divide en un paquete `src/api/v1/`:
- `routes_health.py`: Health check, diagnóstico y salto a versión 2.0.0.
- `routes_dashboard.py`: Resumen ejecutivo de balance y saldos reales.
- `routes_asistencia.py`: Marcación laboral, consulta de períodos y materias universitarias.
- `routes_movimientos.py`: Registro de gastos e ingresos, OCR fiscal y listado.
- `routes_obligaciones.py`: Catálogo de deudas, abonos, timeline de vencimientos y proyector de capacidad de pago.
- `routes_avisos.py`: Agendamiento y recordatorios sincronizados con Calendar.
- `routes_cierres.py`: Cierres contables y laborales, descarga de PDFs.
- `routes_clima.py`: Datos meteorológicos para el dashboard y notificaciones móviles.
- `routes_soporte.py`: Mesa de ayuda y consulta de logs de telemetría.

---

## 4. LO QUE QUEDA EXPLÍCITAMENTE FUERA DE ALCANCE (NO-SCOPE)

1. **Conciliación Bancaria Automatizada:** Descartada por la complejidad de conexión con múltiples entidades financieras paraguayas y bajo retorno de valor inmediato.
2. **Cálculo de Honorarios o Liquidación Docente:** Descartado; el usuario es estudiante cursante.
3. **Manejo de Clases Extraordinarias Complejas:** No requerido para la asistencia del alumno.
4. **WebSockets o Conexiones Persistentes:** Incompatibles con la restricción del único worker WSGI en PythonAnywhere.
5. **Autenticación Multi-Tenant Compleja:** El sistema se mantiene mono-usuario en esta fase para preservar la ligereza del runtime.
