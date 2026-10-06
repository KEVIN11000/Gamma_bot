# Checklist de Tareas (Gastos Fijos GUI)

- [x] 1. **Implementar sanitizador `safe_int`**: Añadir la función a la capa lógica y sus tests unitarios asociados (verificando inputs como "Gs. 150.000", "150000", "Gs 10.500").
- [x] 2. **Desarrollar operaciones de lectura en Sheets**: Implementar `obtener_gastos_fijos` en la capa lógica para parsear la pestaña `Presupuesto_Base` y agrupar por categoría. Escribir tests utilizando mocks.
- [x] 3. **Desarrollar operaciones de escritura en Sheets**: Implementar `actualizar_monto_gasto_fijo` y `agregar_gasto_fijo`. Escribir tests mockeados de inserción y actualización.
- [x] 4. **Comandos Principales y UI Base**: Modificar los handlers de presentación para atrapar `/fijos` y `/gastos_fijos`, retornando el teclado inline principal de 3 opciones (Desglose, Modificar, Registrar).
- [x] 5. **Flujo de Callback: `fijos_ver`**: Implementar handler para el bot_action que muestra el desglose leído desde `obtener_gastos_fijos`.
- [x] 6. **Flujo de Callback y Wizard: `fijos_editar`**: Implementar la selección del concepto y la captura del nuevo monto usando `register_next_step_handler`. Integrar guardado.
- [x] 7. **Flujo de Callback y Wizard: `fijos_nuevo`**: Implementar pasos secuenciales de alta (Categoría -> Concepto -> Monto -> Confirmación) y guardado.
- [x] 8. **Patrón Dual**: Refactorizar/Conectar los comandos directos (`/fijo_set` y `/fijo_nuevo`) para que consuman la misma lógica de negocio sin interactividad.
- [x] 9. **Calidad y Verificación**: Correr `black`, `flake8` y la suite de `pytest`. Resolver lints pendientes según ticket original (PEP 8, longitud 120, sin sentencias múltiples en E701).
