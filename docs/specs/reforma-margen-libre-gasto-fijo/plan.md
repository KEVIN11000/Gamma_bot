# Plan Arquitectónico (Plan): Reforma del Margen Libre y Atributo Booleano de Gasto Fijo

## 1. Arquitectura de Datos y Contratos DTO

### A. Extensión de `Obligaciones_Maestro`
Se añade el encabezado `Es_Gasto_Fijo` a la lista `ENCABEZADOS_OBLIGACIONES_MAESTRO` en `src/logic/constants.py`:

```python
ENCABEZADOS_OBLIGACIONES_MAESTRO = [
    "ID_Obligacion",
    "Tipo",
    "Nombre",
    "Entidad",
    "Monto_Inicial",
    "Saldo_Actual",
    "Estado",
    "Cuota_Referencia_Gs",
    "Fecha_Inicio",
    "Observaciones",
    "Cuotas",
    "Event_ID",
    "Dia_Vencimiento",
    "Cuotas_Totales",
    "Cuotas_Restantes",
    "Orden_Prioridad",
    "Es_Gasto_Fijo",  # Nueva columna booleana (1 o 0)
]
```

### B. Contratos Pydantic en `src/api/schemas.py`
Se actualizan los modelos de obligaciones para exponer y validar el campo:

```python
class ObligacionBase(BaseModel):
    # ... campos existentes ...
    es_gasto_fijo: bool = Field(
        default=True,
        description="True si la cuota se considera un gasto fijo estructural que deduce margen libre",
    )


class ObligacionCreate(ObligacionBase):
    pass


class ObligacionUpdate(BaseModel):
    # ... campos existentes opcionales ...
    es_gasto_fijo: Optional[bool] = None


class ObligacionResponse(ObligacionBase):
    id_obligacion: str
    estado: str
    es_gasto_fijo: bool
```

---

## 2. Lógica de Dominio y Fórmulas (`src/logic/financiero.py`)

### A. Función `calcular_margen_de_ataque()`
Modificación de la selección de deudas activas para considerar `Es_Gasto_Fijo`:

```python
def calcular_margen_de_ataque() -> int:
    repo = SheetsRepository()
    ingresos_base, gastos_fijos = repo.obtener_presupuesto_base_completo()

    # Fallback dinámico si Presupuesto_Base no tiene ingresos registrados (TCK-004)
    if ingresos_base <= 0:
        salario_fallback = repo.obtener_ultimo_salario_libro_diario()
        if salario_fallback > 0:
            ingresos_base = salario_fallback

    # Filtrar obligaciones activas y computables como gasto fijo
    deudas = repo.get_obligaciones_activas()
    deudas_fijas = []
    for d in deudas:
        estado = str(d.get("Estado", "")).strip().lower()
        if estado in ("pausado", "pausada", "cancelado", "pagado"):
            continue

        # Si el campo existe, evaluar verdad; por compatibilidad default True si tiene cuota > 0
        raw_fijo = str(d.get("Es_Gasto_Fijo", "1")).strip().lower()
        es_fijo = raw_fijo in ("1", "true", "si", "yes", "t")
        if es_fijo:
            deudas_fijas.append(d)

    suma_cuotas = sum(safe_int(d.get("Cuota_Referencia_Gs", 0)) for d in deudas_fijas)
    margen = ingresos_base - gastos_fijos - suma_cuotas
    return max(0, margen)
```

### B. Desactivación Reactiva al Pausar Deudas
En `alta_obligacion`, `actualizar_estado_obligacion` o los endpoints de actualización (`routes_obligaciones.py`):
- Si `estado` cambia a `"Pausado"` o `"Pausada"`, automáticamente `Es_Gasto_Fijo` se actualiza a `0` (o se desmarca).
- Si `estado` se reactiva a `"Activo"`, se restablece a `1` a menos que explícitamente se configure lo contrario.
- Tras la mutación, se invoca `_sheets_cache.clear()` para que el dashboard y proyecciones recalculen el margen libre de forma reactiva instantánea.

### C. Limpieza del Fallback en `routes_dashboard.py`
Reemplazo de la fórmula histórica de fallback:
```python
# ANTES:
margen_libre = max(0, flujo_neto - int(gastos * 0.2))

# DESPUÉS:
# Si el cálculo estructurado falla, no viciar con gastos diarios:
margen_libre = max(0, ingresos - gastos_fijos)
```

---

## 3. Plan de Pruebas Unitarias y de Integración

1. **`tests/test_financiero_margen_libre.py`:**
   - Verificar que el registro de gastos diarios en Libro Diario no modifica `calcular_margen_de_ataque()`.
   - Verificar que una deuda con `Es_Gasto_Fijo = 1` deduce su cuota.
   - Verificar que una deuda con `Es_Gasto_Fijo = 0` NO deduce su cuota del margen libre.
   - Verificar que pausar una deuda (`Estado = "Pausado"`) excluye inmediatamente su cuota del margen libre.
2. **`tests/test_routes_obligaciones_gasto_fijo.py`:**
   - Probar `POST /obligaciones` admitiendo `es_gasto_fijo`.
   - Probar `PUT /obligaciones/{id}` con cambio de estado y mutación de `es_gasto_fijo`.
