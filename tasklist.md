# Tasklist: [FEAT] Refactorización de Menús y Estandarización de Modo Dual
**Ticket:** `TICKET-FEAT-10`
**Rama:** `feat/menu-v2-modo-dual`

## Fase 1: Planificación (Completada)
- [x] Auditoría de comandos y mapeo de menú.
- [x] Definición de layout (Grilla 2x2 + 1).
- [x] Aprobación del usuario.

## Fase 2: Arquitectura y Diseño (UX & Backend)
- [ ] **2.1. Refactor de `base.py`:** Diseñar la estructura anidada de callbacks (`menu:finanzas`, `menu:deudas`, etc.) y el teclado dinámico 2x2+1.
- [ ] **2.2. Diseño de Submenús (Nivel 2):** Agrupar y rutear los comandos huérfanos hacia sus botones correspondientes.
- [ ] **2.3. Definición de Estados (FSM):** Crear los nombres de estado en `com.core.states` para los nuevos wizards (`EVALUAR_ABONO_MONTO`, `SIMULAR_MONTO`, etc.).

## Fase 3: Implementación Dev ↔ QA
- [ ] **3.1. Reestructuración Visual:** Modificar el handler `/start` e implementar la navegación entre Nivel 1 y Nivel 2.
- [x] **3.2. Desarrollo de Wizards (Falta de interactividad):**
      - [x] Integrar flujo paso a paso en `/evaluar_abono`.
      - [x] Integrar flujo paso a paso en `/simular`.
      - [x] Integrar flujo paso a paso en `/cierre_mensual`.
      - [x] Integrar teclado base de diagnóstico en `/debug`.
- [x] **3.3. Desarrollo de Fast-Track (Falta de ejecución directa):**
      - [x] Permitir argumentos en `/marcar` (ej: `/marcar entrada`).
      - [x] Permitir argumentos en `/cierre` (ej: `/cierre iva=si`).
      - [x] Permitir argumentos exactos en `/reporte`.
- [ ] **3.4. Pruebas Unitarias y Ajustes:** Ampliar la suite de pytest para probar los nuevos argumentos Fast-Track y las interacciones del teclado anidado.

## Fase 4: Certificación de Integración
- [ ] **4.1. Auditoría Linter:** Validación estricta con `black`, `flake8` y `mypy --no-site-packages`.
- [ ] **4.2. Pruebas de No Regresión:** Asegurar que los comandos legacy siguen operando con normalidad (Dual Mode intacto).
- [ ] **4.3. Pipeline Completion Report & Despliegue.**
