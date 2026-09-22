# Tasklist: [FEAT] Gestión Guiada de Gastos Fijos (UI/UX) - TICKET-FEAT-09

**Ticket:** `TICKET-FEAT-09`
**Versión objetivo:** (A definir, sugerido `v1.16.0` o `v1.15.2`)
**Rama:** `feat/gestion-gastos-fijos-ux-guiada`
**Metodología:** Agency Agents (Pipeline de 4 Fases)

---

## Fase 1: Planificación (agency-project-manager-senior)
- [x] **1.1. Diagnóstico del Ticket:** Leer ticket `ticket_gestion_gastos_fijos.md` y asimilar los requerimientos.
- [x] **1.2. Desglose de Tareas Atómicas:** Redactar este documento (`tasklist.md`) con las tareas verificables.
- [x] **1.3. Aprobación de Plan:** Confirmado con el usuario. Nota: La deuda técnica del linter ya fue resuelta en CI previo.

---

## Fase 2: Arquitectura y Diseño (agency-software-architect, agency-ux-architect)
- [x] **2.1. Diseño de Firmas en Lógica:** Diseñar y estructurar los métodos en `src/logic/logic.py` o módulo equivalente (`safe_int`, `obtener_gastos_fijos`, `actualizar_monto_gasto_fijo`, `agregar_gasto_fijo`).
- [x] **2.2. Diseño de Estados Conversacionales:** Determinar cómo se integrará el asistente interactivo (wizard) con `user_states` o `register_next_step_handler` de telebot.
- [x] **2.3. Definición de Menús y Callbacks:** Trazar el mapeo de callbacks (`fijos_ver`, `fijos_editar`, `fijos_nuevo`) y los botones exactos que se presentarán.

---

## Fase 3: Implementación Dev ↔ QA (agency-frontend-developer, agency-backend-architect, agency-evidence-qa)
- [x] **3.1. Lógica y Persistencia - Funciones Base:**
  - [x] Implementar `safe_int` con expresión regular robusta para limpiar caracteres y devolver enteros.
  - [x] Implementar `obtener_gastos_fijos` filtrando por "Gasto Fijo" y "Fijo" en la base (Google Sheets).
- [x] **3.2. Lógica y Persistencia - Modificación:**
  - [x] Implementar `actualizar_monto_gasto_fijo` y `agregar_gasto_fijo` con validaciones sanitizadas.
- [x] **3.3. Presentación - Menú Principal:**
  - [x] Crear handler para comandos sin argumentos (`/fijos`, `/gastos_fijos`) que despliegue la tarjeta resumen y el `InlineKeyboardMarkup` con 3 opciones.
- [x] **3.4. Presentación - Modo Directo (Dual Support):**
  - [x] Crear handlers para invocación con parámetros atómicos: `/fijo_set` y `/fijo_nuevo` para retrocompatibilidad/scripts.
- [x] **3.5. Callbacks - 🔘 1. Ver Desglose:**
  - [x] Manejador para `fijos_ver` que devuelva un listado detallado agrupado por subcategorías.
- [x] **3.6. Callbacks - 🔘 2. Modificar Monto:**
  - [x] Flujo interactivo paso a paso para `fijos_editar` que solicite selección del concepto y luego pida el monto nuevo, integrando `/cancelar`.
- [x] **3.7. Callbacks - 🔘 3. Registrar Nuevo:**
  - [x] Flujo tipo Wizard interactivo para `fijos_nuevo` pidiendo categoría, concepto y monto.
- [x] **3.8. QA y Pruebas Unitarias:**
  - [x] Desarrollar/actualizar suite en `tests/` para la nueva lógica y los handlers.
  - [x] Ejecutar `pytest tests/ -v`.
  - [x] Resolver conflictos detectados por el linter `flake8` (en particular errores E701 y len > 120), `black` y `mypy`.

---

## Fase 4: Certificación de Integración (agency-reality-checker)
- [x] **4.1. Verificación Cruzada:** Comprobar que el modo guiado y el modo directo operan sin colisionar ni quebrar retrocompatibilidad.
- [x] **4.2. Auditoría Linter & Seguridad:** Asegurar que 100% del código cumpla con las políticas de formato (PEP8/flake8, black).
- [x] **4.3. Pipeline Completion Report:** Documentar cambios, estado de testeo y requerir permiso humano para cierre de fase o merge a `Main-stable`.
