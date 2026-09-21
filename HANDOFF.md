# HANDOFF — Gamma_bot

> [!CAUTION]
> ## 🔒 PROTOCOLO DE GOBERNANZA — LECTURA OBLIGATORIA PARA TODO AGENTE
>
> Todo agente (orquestador o subagente) que trabaje en este repositorio **DEBE** respetar las siguientes reglas sin excepción:
>
> 1. **NUNCA** ejecutes `git push`, `git commit` de cambios funcionales, ni comandos de despliegue sin haber recibido una confirmación **explícita** del usuario ("Aprobado", "Desplegar", "Procede", etc.).
> 2. **La aprobación del plan de implementación NO es aprobación de despliegue.** Son dos gates separados e independientes.
> 3. El flujo correcto es siempre:
>    ```
>    QA verde → Pipeline Completion Report → PAUSA → [Usuario: "Aprobado"] → Push
>    ```
> 4. Los subagentes de desarrollo (`agency-frontend-developer`, `agency-backend-architect`, etc.) **NUNCA** hacen push directamente. Solo el orquestador puede hacerlo, y únicamente tras autorización humana.
> 5. Violar este protocolo es una infracción de gobernanza que debe reportarse al usuario de forma transparente e inmediata.

**Fase cerrada:** v1.14.2 (Restauración de Retrocompatibilidad, Persistencia de Estados y Robustez de Cola)  
**Fecha de cierre:** 2026-09-21  
**Estado del build/tests:** ✅ pasando — 127 tests pasando al 100% (8.03s), Black, Flake8, Mypy y Bandit limpios.

---

## 1. Estado Actual
- **Modo Dual (OCP):** Comandos directos inmediatos funcionales (`/gasto 50000 Almuerzo`, `/ingreso 200000 Salario`, `/nueva_deuda ...`, `/abonar ...`), y flujos conversacionales interactivos cuando se llaman sin argumentos.
- **Persistencia de Estados (Stateless WSGI):** `src/com/core/states.py` persistiendo estados en SQLite (`user_states`) con fallback en memoria.
- **Validadores Centralizados (DRY):** `src/com/utils/validators.py` para montos, fechas, categorías y cuotas.
- **Robustez de Cola:** `src/app_queue/worker.py` con despacho real de operaciones, generación física y envío de reportes PDF, reintentos exponenciales y fallback síncrono.
- **Mapeo Resiliente de Google Sheets:** `src/repositories/sheets_repository.py` utilizando `_get_records(ws, expected_headers)` con fallback dinámico transparente a `expected_headers=[]`.
- **Pruebas Locales:** Verificadas y confirmadas en vivo por el usuario en Telegram (`@BeaterK11000_bot`).
- **Webhook de Producción:** Restaurado exitosamente a `https://kevin11000.pythonanywhere.com`.

---

## 2. Decisiones Tomadas en Esta Fase
- **Decisión:** Soportar Modo Dual (OCP) en todos los handlers financieros y de deudas.
  **Por qué:** Permitir tanto interacción ágil por texto para usuarios avanzados como asistencia guiada para flujos exploratorios sin romper contratos existentes.
- **Decisión:** Persistir estados conversacionales en la tabla `user_states` de `cola.db`.
  **Por qué:** Erradicar la pérdida de estados conversacionales al reciclarse workers en entornos WSGI (PythonAnywhere).
- **Decisión:** Método resiliente `_get_records` en `SheetsRepository`.
  **Por qué:** Evita que diferencias entre los esquemas declarados en código y las columnas reales en Google Drive generen excepciones `GSpreadException`.
- **Decisión:** Generación y entrega directa de PDF en el worker de cola.
  **Por qué:** Garantiza que las peticiones encoladas de `/reporte` no mueran silenciosamente y entreguen el documento binario al usuario.

---

## 3. Archivos y Módulos Clave Tocados

| Archivo | Cambio |
|---|---|
| `src/com/utils/validators.py` | [NUEVO] Validadores y sanitizadores de datos reutilizables. |
| `src/com/core/states.py` | Máquina de estados respaldada en SQLite con fallback en memoria. |
| `src/com/handlers/finanzas.py` | Modo dual para `/gasto` e `/ingreso`. |
| `src/com/handlers/deudas.py` | Modo dual para `/nueva_deuda` y `/abonar`. |
| `src/com/handlers/base.py` | Comando `/cancelar` unificado y menús. |
| `src/repositories/sheets_repository.py` | Lectura resiliente de registros con constantes de dominio. |
| `src/app_queue/worker.py` | Despacho real de operaciones contables y generación/envío de PDF. |
| `src/run_bot.py` | Habilitado worker local en segundo plano para pruebas en polling. |
| `tests/` | 127 tests unitarios y de integración cubriendo validadores, estados, worker y modo dual. |

---

## 4. Pendientes Explícitos para la Próxima Fase
- [ ] Configurar externamente el job en cron-job.org para invocar `GET https://kevin11000.pythonanywhere.com/cron/procesar-cola` cada 1 a 5 minutos con el header `X-Cron-Secret`.
- [ ] Desplegar formalmente v1.14.2 al repositorio remoto y servidor de producción tras aprobación humana.

---

## 5. Cómo Verificar que Este Handoff Sigue Vigente
```bash
pytest tests/ -v
black --check .
flake8 . --max-line-length=88 --extend-ignore=E501,W293,F821,E402,E203,F401
mypy .
```
Todos los comandos deben finalizar con código de salida `0`.
