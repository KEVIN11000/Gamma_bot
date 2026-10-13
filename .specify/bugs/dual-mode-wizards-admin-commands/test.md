# Bug Test Verification: Flujos con Wizard / Modo Dual en Botones y Comandos Administrativos

- **Slug**: dual-mode-wizards-admin-commands
- **Verified At**: 2026-10-13T12:43:00-03:00

## Verification Summary

- **Suites Ejecutadas**:
  - `pytest tests/test_handlers_deudas.py tests/test_handlers_base.py`
  - `pytest tests/test_modo_dual.py`
- **Resultados**: 27/27 tests superados (100% passed).
- **Casos Específicos Verificados**:
  1. `test_handle_estrategia_interactivo`: Comprueba que `/estrategia` sin argumentos genera el selector interactivo con `reply_markup` y botones inline.
  2. `test_handle_estrategia_directo`: Comprueba que `/estrategia saldo` invoca directamente `proyectar_cola_deudas("saldo")` sin pasar por el wizard.
  3. `test_callback_estrategia_sel`: Comprueba que al presionar un botón del selector se confirma el callback query y se despacha el mensaje simulado.
  4. `test_registrar_comandos_menu_prod`: Comprueba que en producción se registran 23 comandos (incluyendo `/cancelar`, `/fijos`, `/estrategia`, `/foco`, `/evaluar_abono`, `/vencimientos`, sin `/debug`).
  5. `test_registrar_comandos_menu_dev`: Comprueba que en modo dev se añade `/debug` como comando número 24.
