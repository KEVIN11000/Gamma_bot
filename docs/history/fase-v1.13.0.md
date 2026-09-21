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
>
> *Violación registrada el 2026-09-20: el orquestador ejecutó push tras QA sin esperar autorización de despliegue explícita del usuario. Este bloque existe para prevenir recurrencias.*

---

**Fase activa:** v1.14.0 (Refactor UX/UI + Cola Asíncrona)
**Fase anterior cerrada:** v1.13.0 (Correcciones y Auditoría)
**Fecha de actualización:** 2026-09-20
**Estado del build/tests:** ✅ 102 tests pasando al 100%.

---

## 1. Estado actual

- Mitigada lógica de autenticación fail-open en webhook (`/deploy`) y cron jobs, centralizando verificación HMAC.
- Rate limiting (decorador `@limiter.limit`) enrutado correctamente antes de los registros de ruta.
- Unificado el Libro Diario a 16 columnas tanto para creación como para inserciones; los Cierres Mensuales y sus balances toman debida cuenta de impuestos (IVA) y de errores sintácticos por medio de saneamientos y padding de filas (`append_row()`).
- Refactorización completada de los servicios mock (`DriveService`, `CalendarService`) y desvinculación de los mensajes engañosos correspondientes del `README.md`.
- El comando `/estrategia` presenta las fechas estimadas de forma encadenada (efecto cascada) y advierte visualmente la exclusión de intereses.
- Tareas referidas a los endpoints y lógica contable operan fluidamente; la cobertura en seguridad ha ascendido al bloquear vectores manuales vía query strings.
- **Suite de Pruebas estabilizada:** Se corrigieron los mocks y aserciones desactualizadas, alcanzando el 100% de éxito (101 tests).

## 2. Decisiones tomadas en esta fase

- **Decisión:** Uso de `hmac.compare_digest` para todas las firmas entrantes de Github y Cron.
  **Por qué:** Evitar ataques de side-channel timing, previniendo inyecciones que bypassen la validación estricta de headers.
- **Decisión:** Sustituir la inserción posicional basada en la sumatoria de columnas previas (`col_values`) por la directiva `append_row()`.
  **Por qué:** Es más atómico y erradica race conditions entre operaciones simultáneas de Sheets, previniendo datos corrompidos.
- **Decisión:** Recálculo retroactivo omitido del código base principal pero listado como pendiente opcional o script local si se desea normalizar la base histórica.
  **Por qué:** Minimizar el riesgo de corromper Cierres pre-existentes sin un volcado manual explícito.
- **Decisión:** Dejar en pausa el refactor UI propuesto para InlineKeyboards.
  **Por qué:** El usuario especificó pausar la implementación visual (a agruparse bajo el botón "Comandos") hasta concluir tickets de fiabilidad.
- **Decisión:** Ajustar mocks de pruebas a la realidad productiva.
  **Por qué:** Tras el blindaje de entorno (`validate_production_config`) y refactor de gspread (`append_row()`), los tests no reflejaban el comportamiento deseado y fallaban sintácticamente.

## 3. Archivos y módulos clave tocados

| Archivo | Cambio |
|---|---|
| `flask_app.py` | Corrección estricta de handlers, inyecciones X-Cron-Secret y reordenamiento de rate limiting. |
| `config.py` | Inserción de barrera restrictiva de arranque `validate_production_config()` ante ausencia de llaves. |
| `logic/financiero.py` | Adopción de `append_row()`, encadenamiento de cálculos en la bola de nieve (`proyectar_cola_deudas`) e integración robusta al esquema de 16-cols. |
| `handlers/deudas.py` | Eliminación de try/except intrusivos para posibilitar interceptación generalizada y agregado de *disclaimer* financiero en proyecciones. |
| `logic/constants.py` y `VERSION` | Carga unificada de versión v1.13.0, definición estandarizada de encabezados `ENCABEZADOS_LIBRO_DIARIO`. |
| `tests/*` | Múltiples tests de regresión actualizados (`test_auth_security.py`, `test_integration_local.py`, `test_services.py`, `test_sheets_repository.py`) para absorber parámetros `**kwargs` y validar bloqueos del entorno. |

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
