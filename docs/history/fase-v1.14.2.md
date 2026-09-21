# HISTÓRICO DE FASE — v1.14.2: Restauración de Retrocompatibilidad, Persistencia de Estados y Robustez de Cola

> [!CAUTION]
> ## 🔒 PROTOCOLO DE GOBERNANZA — LECTURA OBLIGATORIA PARA TODO AGENTE
> 1. **NUNCA** ejecutes `git push`, `git commit` de cambios funcionales, ni comandos de despliegue sin confirmación **explícita** del usuario.
> 2. La aprobación del plan no es aprobación de despliegue.
> 3. El pipeline debe ser 100% verde antes de solicitar la aprobación de despliegue.

**Fase cerrada:** v1.14.2 (Estabilidad, Modo Dual OCP, Persistencia SQLite y Worker Robusto)  
**Fecha de cierre:** 2026-09-21  
**Estado del build/tests:** ✅ pasando — 127 tests pasando al 100% (8.03s), Black, Flake8, Mypy y Bandit limpios.

---

## 1. Estado Actual del Sistema
- **Modo Dual (OCP):**
  - Comandos directos inmediatos: `/gasto <monto> <desc>`, `/ingreso <monto> <desc>`, `/nueva_deuda <entidad> <concepto> <monto> <cuotas> <fecha> [dia]` y `/abonar <id> <monto> [fecha] [tasa_iva]`.
  - Asistente guiado interactivo por botones cuando se invocan sin argumentos (`/gasto`, `/ingreso`, `/nueva_deuda`, `/abonar`).
  - Comando `/cancelar` unificado globalmente en `base.py`.
- **Persistencia de Estados en SQLite:**
  - `src/com/core/states.py` almacena los estados de conversación en la tabla `user_states` de SQLite con `timeout=15.0` y caché en memoria RAM. Es resiliente a reinicios de workers en WSGI (PythonAnywhere).
- **Validadores Centralizados (DRY):**
  - Módulo `src/com/utils/validators.py` con validación y normalización de montos, fechas, categorías y cuotas.
- **Robustez de Cola y Despachador:**
  - `src/app_queue/worker.py` despacha operaciones reales (`registrar_movimiento`, `create_debt`, `register_payment`, `crear_aviso_calendar`, `generar_reporte`).
  - Soporta fallback síncrono ante fallos y reintentos exponenciales con `timeout=15.0`.
  - Genera y envía documentos PDF reales a Telegram para la operación `generar_reporte`.
- **Mapeo Resiliente de Encabezados:**
  - `src/repositories/sheets_repository.py` implementa `_get_records(ws, expected_headers)` con fallback transparente a `expected_headers=[]` ante columnas no presentes en hojas remotas heredadas de producción.
- **Pruebas Locales Exitosas:**
  - Bot probado en vivo en polling local con worker periódico de fondo; flujos validados y confirmados por el usuario.
  - Webhook de producción hacia PythonAnywhere restaurado de forma segura.

---

## 2. Decisiones Técnicas Tomadas
1. **Modo Dual con Soporte OCP:** Se desacopló la verificación de argumentos posicionales de la máquina de estados; si existen argumentos se procesa directamente la transacción contable sin ingresar al state store.
2. **Fallback Dinámico en Google Sheets:** Para evitar que diferencias entre la definición estática de dominio y las columnas reales en Google Drive rompan `gspread >= 6.0`, se encapsuló la lectura con fallback dinámico seguro.
3. **Despacho Completo de Reportes PDF en Cola:** Se integró `PDFService.generar_reporte_generico` y `bot.send_document` dentro del worker asíncrono para que las solicitudes encoladas entreguen el binario al usuario.

---

## 3. Archivos Modificados y Creados
- `src/com/utils/validators.py` & `src/com/utils/__init__.py` [NUEVO]
- `tests/test_validators.py`, `tests/test_states.py`, `tests/test_worker.py`, `tests/test_modo_dual.py` [NUEVOS]
- `src/com/core/states.py` [REFACTORIZADO A SQLITE]
- `src/com/handlers/finanzas.py`, `src/com/handlers/deudas.py`, `src/com/handlers/base.py` [MODO DUAL]
- `src/app_queue/worker.py` [DISPATCH REAL & PDF SEND]
- `src/repositories/sheets_repository.py` [ENCABEZADOS & LECTURA RESILIENTE]
- `src/run_bot.py` [WORKER THREAD LOCAL]
