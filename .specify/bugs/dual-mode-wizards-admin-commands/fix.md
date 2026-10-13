# Bug Fix: Flujos con Wizard / Modo Dual en Botones y Comandos Administrativos

- **Slug**: dual-mode-wizards-admin-commands
- **Fixed At**: 2026-10-13T12:43:00-03:00

## Description of Fix

1. **Modo Dual y Selector Interactivo en Estrategia de Pagos**:
   En `src/com/handlers/deudas.py`:
   - Se actualizó el comando `/estrategia` (y el botón de menú `accion:estrategia`) para que, al invocarse sin argumentos, despliegue un selector interactivo con botones inline (`🎯 Por Prioridad / Urgencia` y `💰 Menor Saldo (Bola de Nieve)`).
   - Se añadió el manejador de callback `estrategia_sel:` para procesar la opción elegida y retornar la proyección correspondiente.
   - Se mantuvo la ejecución directa cuando el comando incluye argumentos explícitos (`/estrategia prioridad` o `/estrategia saldo`).
2. **Sincronización de Comandos Administrativos de Negocio en Menú**:
   En `src/com/handlers/base.py`:
   - Se integraron formalmente en `_registrar_comandos_menu(bot)` los comandos administrativos útiles existentes que faltaban en el menú principal:
     - `/cancelar` (Cancelar cualquier operación o flujo activo).
     - `/fijos` (Administrar presupuesto de gastos fijos).
     - `/estrategia` (Ver estrategia bola de nieve y orden de pago).
     - `/foco` (Ver la próxima deuda objetivo a liquidar).
     - `/evaluar_abono` (Simular impacto de abono extraordinario).
     - `/vencimientos` (Ver calendario de vencimientos de deudas).
   - Se preservó `/debug` estrictamente como comando exclusivo para entorno de desarrollo técnico (`MODO_DESARROLLADOR="True"`).
   - Se reestructuró la salida del comando `/comandos` para agrupar sistemáticamente todas las opciones por dominio funcional (General & Control, Finanzas & Presupuesto, Deudas & Estrategia, Asistencia & Horarios, Avisos & Agenda, y Técnico).

## Files Modified

- `src/com/handlers/deudas.py`
- `src/com/handlers/base.py`
- `tests/test_handlers_base.py`
- `tests/test_handlers_deudas.py`
