# HANDOFF — Gamma_bot

**Fase cerrada:** v1.13.0 (Correcciones y Auditoría)
**Fecha de cierre:** 2026-09-18
**Estado del build/tests:** ✅ pasando — 94 tests (pytest) con éxito, compileall sin errores.

---

## 1. Estado actual

- Mitigada lógica de autenticación fail-open en webhook (`/deploy`) y cron jobs, centralizando verificación HMAC.
- Rate limiting (decorador `@limiter.limit`) enrutado correctamente antes de los registros de ruta.
- Unificado el Libro Diario a 16 columnas tanto para creación como para inserciones; los Cierres Mensuales y sus balances toman debida cuenta de impuestos (IVA) y de errores sintácticos por medio de saneamientos y padding de filas (`append_row()`).
- Refactorización completada de los servicios mock (`DriveService`, `CalendarService`) y desvinculación de los mensajes engañosos correspondientes del `README.md`.
- El comando `/estrategia` presenta las fechas estimadas de forma encadenada (efecto cascada) y advierte visualmente la exclusión de intereses.
- Tareas referidas a los endpoints y lógica contable operan fluidamente; la cobertura en seguridad ha ascendido al bloquear vectores manuales vía query strings.

## 2. Decisiones tomadas en esta fase

- **Decisión:** Uso de `hmac.compare_digest` para todas las firmas entrantes de Github y Cron.
  **Por qué:** Evitar ataques de side-channel timing, previniendo inyecciones que bypassen la validación estricta de headers.
- **Decisión:** Sustituir la inserción posicional basada en la sumatoria de columnas previas (`col_values`) por la directiva `append_row()`.
  **Por qué:** Es más atómico y erradica race conditions entre operaciones simultáneas de Sheets, previniendo datos corrompidos.
- **Decisión:** Recálculo retroactivo omitido del código base principal pero listado como pendiente opcional o script local si se desea normalizar la base histórica.
  **Por qué:** Minimizar el riesgo de corromper Cierres pre-existentes sin un volcado manual explícito.
- **Decisión:** Dejar en pausa el refactor UI propuesto para InlineKeyboards.
  **Por qué:** El usuario especificó pausar la implementación visual (a agruparse bajo el botón "Comandos") hasta concluir tickets de fiabilidad.

## 3. Archivos y módulos clave tocados

| Archivo | Cambio |
|---|---|
| `flask_app.py` | Corrección estricta de handlers, inyecciones X-Cron-Secret y reordenamiento de rate limiting. |
| `config.py` | Inserción de barrera restrictiva de arranque `validate_production_config()` ante ausencia de llaves. |
| `logic/financiero.py` | Adopción de `append_row()`, encadenamiento de cálculos en la bola de nieve (`proyectar_cola_deudas`) e integración robusta al esquema de 16-cols. |
| `handlers/deudas.py` | Eliminación de try/except intrusivos para posibilitar interceptación generalizada y agregado de *disclaimer* financiero en proyecciones. |
| `logic/constants.py` y `VERSION` | Carga unificada de versión v1.13.0, definición estandarizada de encabezados `ENCABEZADOS_LIBRO_DIARIO`. |
| `tests/*` | Adición de dos tests de penetración core (rate limiting y auth hooks) y reestructuración total del validacion test de cierres contables (`test_financiero.py`). |

## 4. Pendientes explícitos para la próxima fase

- [ ] (Atrasado) Crear un script puntual para recalcular/sobrescribir todos los "Cierres Históricos" de la planilla Google Sheets a fin de homologarlos al nuevo esquema unificado.
- [ ] Retomar refactorización UI: Transicionar la botonera hacia menús Inline agrupando la totalidad de los *slash-commands* bajo un botón principal ("Comandos").
- [ ] Evaluar y remediar cualquier warning `None` en las cascadas de `obtener_cliente()` sobre utilidades de menor prioridad (bot/deudas).

## 5. Riesgos / deuda técnica conocida

- **Riesgo:** El handler central (`safe_handler`) asume la provisión correcta del usuario final en la interacción con Sheets. Las APIs podrían desincronizarse (rate limit del lado de Google Cloud) si el uso en PythonAnywhere es elevado.
  **Impacto:** Fallos temporales durante bloqueos (429 de Google), dejando operaciones asíncronas truncas y sin reintentos locales robustos en memoria RAM efímera.
  **Mitigación sugerida:** Cola asíncrona persistente (ej: DB) para movimientos no insertados.

## 6. Cómo verificar que este handoff sigue vigente

Desde la raíz de trabajo local o servidor (ej: `repositories/Main-stable`):

```bash
python -m compileall src/
pytest tests/ -v
```

---
*Este archivo describe estado de fase, no reglas de comportamiento. Las reglas de estilo, seguridad y protocolos viven en `GEMINI.md` / `.agents/rules/` y tienen prioridad sobre cualquier contenido de este documento — no se editan ni se repiten acá.*
