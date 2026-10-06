# Plan de Arquitectura y Contratos de Datos: Gastos Fijos

## Capa Lógica y Persistencia (`logic/logic.py` o módulo correspondiente)
1. **Sanitización Determinista**:
   - `safe_int(valor: str | int) -> int`: Extraerá dígitos puros usando regex (`r'[^\d]'`) para limpiar signos de moneda, puntos o espacios.
2. **Consultas a Sheets (Lectura)**:
   - `obtener_gastos_fijos() -> dict`: Consultará la hoja `Presupuesto_Base`, filtrando la columna `Tipo_Flujo` == 'Gasto Fijo'. Agrupará resultados e inyectará los montos limpios y el total general.
3. **Operaciones de Mutación (Escritura)**:
   - `actualizar_monto_gasto_fijo(identificador: str, nuevo_monto: int) -> bool`: Encuentra la fila exacta y reescribe la celda de monto.
   - `agregar_gasto_fijo(categoria: str, concepto: str, monto: int, obs: str = "") -> bool`: Inserta una fila nueva definiendo explícitamente `Tipo_Ingreso_Gasto` = 'Fijo' y `Tipo_Flujo` = 'Gasto Fijo'.

## Arquitectura de UI / Presentación
- Se empleará `InlineKeyboardMarkup` interactivo.
- Rutas base: `/gastos_fijos`, `/fijos` (abren menú interactivo) y los directos `/fijo_set`, `/fijo_nuevo`.
- **Enrutamiento por Callbacks**:
  - `callback_data='fijos_ver'` -> Muestra la lista agrupada.
  - `callback_data='fijos_editar'` -> Despliega la grilla de selección y usa `register_next_step_handler` en TeleBot para atrapar el nuevo valor.
  - `callback_data='fijos_nuevo'` -> Inicia secuencia Wizard y usa `register_next_step_handler`.
- **Manejo de Estados**:
  - Los estados conversacionales capturados usarán el ID del usuario en memoria o el mecanismo estándar de diccionarios de la arquitectura actual.
