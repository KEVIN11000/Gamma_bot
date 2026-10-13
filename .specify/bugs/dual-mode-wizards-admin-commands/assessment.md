# Bug Assessment: Flujos con Wizard / Modo Dual en Botones y Comandos Administrativos

- **Slug**: dual-mode-wizards-admin-commands
- **Created**: 2026-10-13T12:40:00-03:00
- **Source**: Telegram Soporte Ticket `TG-ea4b0c5b` (`repositories/Main-stable/tickets/in_progress/TICKET-TG-ea4b0c5b.md`)
- **Verdict**: valid
- **Severity**: low

## Report (verbatim or summarized)

> "Necesito convertir todos los botones a flujos con wizard o modo dual y agregar en admin comandos útiles que faltan excepto comandos exclusivos para técnico"
> — Usuario: @Kl4lT0 (2026-09-21T17:57:58Z)

## Symptom

1. **Botones sin selector interactivo guiado**: El botón "Estrategia" (`accion:estrategia`) invoca `/estrategia` ejecutando directamente la opción por defecto sin permitir elegir entre priorización de pagos o bola de nieve. Similarmente, `/balance` no ofrece opciones interactivas complementarias ni selector de períodos.
2. **Comandos administrativos útiles omitidos en menú principal y comando `/comandos`**: Comandos de gestión y negocio implementados en el bot (`/cancelar`, `/fijos`, `/estrategia`, `/foco`, `/evaluar_abono`, `/vencimientos`) no aparecen registrados en el menú nativo de Telegram (`_registrar_comandos_menu`) ni en la lista descriptiva de `/comandos`, dificultando la administración integral al usuario sin tener que recordar la sintaxis exacta de memoria.
3. **Comandos exclusivos para técnico deben mantenerse separados**: Comandos de bajo nivel de ingeniería (`/debug`) deben permanecer exclusivos del entorno de depuración técnica (`MODO_DESARROLLADOR=true`), sin mezclarse con la operativa administrativa regular.

## Reproduction

1. Pulsar el botón "Estrategia" en el menú de Deudas: se ejecuta directamente la estrategia por prioridad sin consultar al usuario si prefiere ver la bola de nieve por menor saldo.
2. Ejecutar `/comandos`: observar que faltan comandos de uso frecuente como `/cancelar`, `/fijos`, `/estrategia`, `/foco`, `/evaluar_abono`, `/vencimientos`.
3. Abrir el menú emergente de comandos de Telegram (`/`): no incluye los comandos administrativos de negocio.

## Suspected Code Paths

- `src/com/handlers/base.py:17-43` — `_registrar_comandos_menu(bot)`: lista de comandos nativos de Telegram.
- `src/com/handlers/base.py:267-306` — `comando_comandos(message)`: listado textual de comandos y categorías.
- `src/com/handlers/deudas.py:220-252` — `handle_estrategia(message)`: manejo de `/estrategia`.
- `src/com/handlers/deudas.py:307-330` — Callbacks de selección interactiva de deudas y estrategias.

## Root Cause Hypothesis

Los comandos funcionales fueron desarrollándose de forma modular en `deudas.py` y `finanzas.py`, pero la centralización de comandos de menú en `base.py` no fue sincronizada con la suite completa de comandos administrativos. Asimismo, `/estrategia` carecía de un submenú guiado de selección cuando se llamaba sin parámetros directos.

## Proposed Remediation

**Preferred**:
1. En `src/com/handlers/deudas.py`:
   - Enriquecer `handle_estrategia`: si se invoca sin argumentos (`/estrategia` o botón `accion:estrategia`), mostrar un teclado inline interactivo con opciones:
     - `🎯 Por Prioridad (Urgencia)` (`callback_data="estrategia_sel:prioridad"`)
     - `💰 Por Menor Saldo (Bola de Nieve)` (`callback_data="estrategia_sel:saldo"`)
   - Si se invoca con argumento directo (`/estrategia prioridad` o `/estrategia saldo`), responder de inmediato (modo dual preservado).
   - Añadir handler de callback para `estrategia_sel:`.
2. En `src/com/handlers/base.py`:
   - Añadir en `_registrar_comandos_menu(bot)` los comandos administrativos de negocio:
     - `cancelar`: "Cancelar cualquier operación o flujo activo"
     - `fijos`: "Administrar gastos fijos del presupuesto"
     - `estrategia`: "Ver estrategia bola de nieve y orden de pago"
     - `foco`: "Ver la próxima deuda objetivo a liquidar"
     - `evaluar_abono`: "Simular impacto de abono extraordinario"
     - `vencimientos`: "Ver calendario de vencimientos de deudas"
   - Actualizar `comando_comandos` para clasificar claramente las secciones con todos los comandos disponibles, manteniendo `/debug` condicionado a `MODO_DESARROLLADOR`.

**Files likely to change**:
- `src/com/handlers/base.py`
- `src/com/handlers/deudas.py`
- `tests/test_handlers_base.py`
- `tests/test_handlers_deudas.py`

**Tests to add or update**:
- Test en `test_handlers_base.py` que compruebe que `_registrar_comandos_menu` registra todos los comandos administrativos y que `/debug` solo se añade en modo desarrollador.
- Test en `test_handlers_deudas.py` que verifique que `/estrategia` sin argumentos muestra teclado inline con opciones de estrategia y que el callback ejecuta la proyección correspondiente.
