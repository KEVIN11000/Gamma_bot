# HANDOFF — Gamma_bot

**Fase cerrada:** v1.14.2 — Restauración de retrocompatibilidad, persistencia de estados y robustez de cola
**Fecha de cierre:** 2026-09-21
**Estado del build/tests:** ✅ pasando — 127 tests pasando al 100% (6.44s), black, flake8 y mypy limpios

---

## 1. Estado actual

- Modo dual operativo en `/gasto` e `/ingreso` (ejecución directa con argumentos inline y flujo guiado interactivo sin argumentos), cubierto por tests en `tests/test_modo_dual.py`.
- Modo dual operativo en `/nueva_deuda` y `/abonar` (ejecución directa y asistente por botones), cubierto por tests en `tests/test_modo_dual.py` y `tests/test_handlers_deudas.py`.
- Cancelación global operativa con `/cancelar` para cualquier flujo guiado en progreso, cubierto por tests en `tests/test_modo_dual.py`.
- Máquina de estados con persistencia en SQLite (`user_states`) y fallback en memoria RAM para resiliencia WSGI, cubierto por tests en `tests/test_states.py`.
- Validadores centralizados de montos, fechas, categorías y cuotas operativos, cubiertos por tests en `tests/test_validators.py`.
- Cola asíncrona en SQLite (`cola.db`) con worker resiliente (`timeout=15.0`, reintentos exponenciales y fallback síncrono), cubierto por tests en `tests/test_worker.py`.
- Despacho real en worker de operaciones de libro diario, registro de deudas, abonos y generación física de reportes PDF con entrega binaria en Telegram (`bot.send_document`), validado en vivo.
- Lectura resiliente de Google Sheets mediante `_get_records()` con fallback automático a `expected_headers=[]` ante discrepancias de columnas remotas, cubierto por tests en `tests/test_sheets_repository.py`.
- Webhook de producción activo hacia `https://kevin11000.pythonanywhere.com`.
- Cron job externo activo para procesamiento periódico en `/cron/procesar-cola`.

## 2. Decisiones tomadas en esta fase

- **Decisión:** Implementar soporte dual (OCP) en comandos financieros y de deudas según la presencia de argumentos inline.
  **Por qué:** Preservar la retrocompatibilidad para usuarios de texto rápido sin sacrificar la asistencia guiada para usuarios interactivos.
- **Decisión:** Persistir la máquina de estados en la tabla SQLite `user_states` en lugar de sólo memoria RAM.
  **Por qué:** Evitar la pérdida de sesiones conversacionales por reciclado de procesos en entornos multi-worker WSGI (PythonAnywhere).
- **Decisión:** Encapsular la lectura de worksheets en `_get_records(ws, expected_headers)` con fallback dinámico.
  **Por qué:** Prevenir excepciones `GSpreadException` cuando las hojas existentes en producción no tienen todas las columnas declaradas en las constantes de dominio.
- **Decisión:** Generar y despachar el documento PDF directamente desde el worker para la operación `generar_reporte`.
  **Por qué:** Eliminar respuestas silenciosas o incompletas cuando el usuario solicita reportes encolados.

## 3. Archivos y módulos clave tocados

| Archivo | Cambio |
|---|---|
| `src/com/utils/validators.py` | Creación de validadores y normalizadores centralizados de datos. |
| `src/com/core/states.py` | Implementación de persistencia SQLite con tabla `user_states` y alias de retrocompatibilidad `_states`. |
| `src/com/handlers/finanzas.py` | Soporte modo dual para `/gasto` e `/ingreso`. |
| `src/com/handlers/deudas.py` | Soporte modo dual para `/nueva_deuda` y `/abonar`. |
| `src/com/handlers/base.py` | Centralización del comando `/cancelar` y gestión de menús. |
| `src/repositories/sheets_repository.py` | Integración de constantes de dominio y método de lectura resiliente `_get_records`. |
| `src/app_queue/worker.py` | Despacho real de operaciones y compilación/envío de reportes PDF vía `bot.send_document`. |
| `src/run_bot.py` | Incorporación de hilo daemon de worker de cola para pruebas locales en polling. |
| `VERSION` | Actualización de versión a `1.14.2`. |
| `tests/` | Suites añadidas y adaptadas (`test_validators.py`, `test_states.py`, `test_worker.py`, `test_modo_dual.py`). |

## 4. Pendientes explícitos para la próxima fase

- [ ] Monitorear logs de producción del endpoint `/cron/procesar-cola` durante 24 horas consecutivas para confirmar ausencia de errores 500 y tasa de reintentos en 0.
- [ ] Implementar migración controlada de columnas en la hoja `Obligaciones_Maestro` de Google Sheets para agregar formalmente las cabeceras `Dia_Vencimiento`, `Cuotas_Totales` y `Cuotas_Restantes`.

## 5. Riesgos / deuda técnica conocida

- **Riesgo:** Inconsistencia de esquema entre hojas de Google Sheets antiguas y nuevas si se añaden columnas requeridas en código sin migrar el spreadsheet.
  **Impacto:** Fallos en `ws.get_all_records` si se remueve el fallback dinámico o si faltan columnas clave como `ID_Obligacion`.
  **Mitigación sugerida:** Mantener activo el método `_get_records()` resiliente y diseñar un script de migración automática de encabezados en el spreadsheet.

## 6. Cómo verificar que este handoff sigue vigente

```bash
pytest tests/ -v
black --check .
flake8 . --max-line-length=88 --extend-ignore=E501,W293,F821,E402,E203,F401
mypy .
```

---
*Este archivo describe estado de fase, no reglas de comportamiento. Las reglas de estilo, seguridad y protocolos viven en `GEMINI.md` / `.agents/rules/` y tienen prioridad sobre cualquier contenido de este documento — no se editan ni se repiten acá.*
