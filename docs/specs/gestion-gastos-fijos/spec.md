# Especificación: Gestión Guiada de Gastos Fijos

## Alcance
Desarrollo de una interfaz de usuario en Telegram (mediante Inline Keyboards) y soporte de backend para consultar, editar y registrar "Gastos Fijos" almacenados en la pestaña `Presupuesto_Base` de Google Sheets. 
Se resolverán problemas de inconsistencia de formato en celdas (ej. "Gs. 156.000" vs numéricos) y se reducirá la fricción del usuario al no requerir memorizar comandos complejos.

## Casos de Uso
1. **Ver Desglose (`fijos_ver`)**: Agrupa rubros por categoría contable (Educación, Servicios, etc.) y muestra subtotales y porcentaje del presupuesto comprometido.
2. **Modificar Monto (`fijos_editar`)**: Flujo interactivo que permite seleccionar un gasto existente mediante botones y cambiar su valor mensual a través de un prompt (con soporte de cancelación vía `/cancelar`).
3. **Registrar Nuevo Gasto (`fijos_nuevo`)**: Asistente (Wizard) que guía al usuario para proveer Categoría, Concepto y Monto, con una tarjeta final de confirmación antes de guardar.

## Restricciones y Patrón Dual (No-Scope)
- **Soporte Dual**: Los comandos directos (`/fijo_set` y `/fijo_nuevo`) DEBEN seguir operando como "Fast-Track" de forma atómica para no romper la compatibilidad con scripts o uso rápido.
- **No-Scope**: No se modifican las lógicas de deuda (`/nueva_deuda` o `/abonar`) ni el simulador. Esta feature está aislada a `Presupuesto_Base` y tipo `Gasto Fijo`.
