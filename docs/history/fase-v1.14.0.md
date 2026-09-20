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

**Fase cerrada:** v1.14.0 (Refactor UX/UI + Cola Asíncrona)
**Fecha de cierre:** 2026-09-20
**Estado del build/tests:** ✅ pasando — 102 tests pasando al 100%.

---

## 1. Estado actual
- Menú principal `/start` renderizado como InlineKeyboardMarkup de 3 niveles de navegación.
- Handlers financieros (`/gasto`, `/ingreso`) y de deudas (`/nueva_deuda`, `/abonar`) convertidos a flujos guiados multi-paso mediante State Machine en memoria por `user_id`.
- Operaciones contra Google Sheets encoladas asíncronamente en SQLite local (`cola.db`).
- Handler de `/comandos` creado y habilitado para mostrar la lista de atajos de texto plano.
- Creación de eventos de avisos y generación de reportes operan usando la cola asíncrona.
- Comando global `/cancelar` habilitado para limpiar estados en curso.
- Tests (102 en total) adaptados y pasando 100% tras los cambios de flujos.

## 2. Decisiones tomadas en esta fase
- **Decisión:** Uso de `app_queue` para la cola en lugar del módulo estándar `queue`.
  **Por qué:** Evitar colisiones de nombres con el paquete base de Python que rompían la aplicación.
- **Decisión:** Implementar la cola con SQLite y un endpoint llamado por cron (`/cron/procesar-cola`).
  **Por qué:** PythonAnywhere gratuito no soporta workers o threads persistentes en background.
- **Decisión:** Persistir el `chat_id` en la base de datos `cola.db`.
  **Por qué:** Para poder enviar notificaciones diferidas al usuario cuando el trabajo termine de procesarse y proveer bases para multitenant.
- **Decisión:** Mantener comandos fallback con argumentos posicionales (ej `/gasto 15000 comida`).
  **Por qué:** Mantener la retrocompatibilidad para usuarios acostumbrados a atajos directos sin navegar los menús.

## 3. Archivos y módulos clave tocados

| Archivo | Cambio |
|---|---|
| `src/app_queue/worker.py` | Nueva implementación de worker FIFO en SQLite con backoff exponencial. |
| `src/com/core/states.py` | Nuevo gestor de State Machine conversacional en memoria. |
| `src/com/handlers/base.py` | Refactor de `/start` a menú inline y adición de `/comandos`. |
| `src/com/handlers/finanzas.py` | Refactor de `/gasto` e `/ingreso` a flujos guiados y encolados. |
| `src/com/handlers/deudas.py` | Refactor de `/nueva_deuda` y `/abonar` a flujos guiados y encolados. |
| `src/flask_app.py` | Inclusión del nuevo endpoint `/cron/procesar-cola`. |
| `HANDOFF.md` | Inserción de protocolo estricto de gobernanza y despliegue humano in-the-loop. |

## 4. Pendientes explícitos para la próxima fase

- [ ] Configurar externamente el job en cron-job.org para invocar `GET https://kevin11000.pythonanywhere.com/cron/procesar-cola` cada 5 minutos con el header `X-Cron-Secret`.
- [ ] Desplegar los cambios al entorno de producción (PythonAnywhere).

## 5. Riesgos / deuda técnica conocida

- **Riesgo:** Si PythonAnywhere reinicia el worker o la memoria se vacía, los estados conversacionales en progreso (State Machine de `states.py`) se perderán ya que solo residen en memoria volátil.
  **Impacto:** Usuarios a mitad de registrar un gasto tendrán que empezar de nuevo y la acción fallará silenciosamente.
  **Mitigación sugerida:** En una futura versión, persistir los estados en SQLite u otra base ligera si la fricción reportada es alta.

## 6. Cómo verificar que este handoff sigue vigente

```bash
pytest tests/ -q
```

---
*Este archivo describe estado de fase, no reglas de comportamiento. Las reglas de estilo, seguridad y protocolos viven en `GEMINI.md` / `.agents/rules/` y tienen prioridad sobre cualquier contenido de este documento — no se editan ni se repiten acá.*
