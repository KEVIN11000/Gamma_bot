# Especificación Funcional (Spec): Reforma del Margen Libre y Atributo Booleano de Gasto Fijo en Obligaciones

## 1. Contexto y Problema Detectado

Actualmente, el sistema financiero de Gamma Bot y Gamma Mobile presenta dos desalineaciones operativas y matemáticas críticas:

1. **Vicio del Margen Libre por Gastos Diarios Operativos:**
   - El **Margen Libre Disponible (MLD)** tiene como propósito conceptual exclusivo brindar perspectiva estructural cada vez que el usuario cobra su ingreso base o proyecta un nuevo compromiso presupuestario (*"¿Cuánto dinero estructural me queda libre después de cubrir mis costos de vida fijos y el servicio de mis deudas obligatorias?"*).
   - En implementaciones previas o fallbacks degradados (ej. en `routes_dashboard.py`), se caía en fórmulas que restaban el gasto diario real (`flujo_neto - int(gastos * 0.2)` o `ingresos - gastos`), provocando que compras cotidianas (como farmacia o almuerzos) disminuyeran erróneamente el margen libre en lugar de afectar únicamente el saldo líquido en caja.

2. **Falta de Discriminación entre Deuda Estructural y Deuda Contingente:**
   - Todas las obligaciones activas en `Obligaciones_Maestro` se computaban por defecto restando su cuota contra el margen mensual, sin permitir clasificar si una obligación constituye un **gasto fijo estructural** recurrente o una obligación esporádica.
   - Si una deuda entra en pausa (`Estado == "Pausado"` o `"Pausada"`), debe existir una variable booleana explícita (`es_gasto_fijo`) que pase a `0` (o `False`), evitando que continúe restando del margen libre estructural mientras esté inactiva.

---

## 2. Alcance (In-Scope)

1. **Alineación Matemática del Margen Libre (MLD):**
   - Garantizar que el cálculo de `margen_libre` en el dashboard y API responda estrictamente a:
     $$\text{MLD} = \text{Ingreso Base} - \text{Gastos Fijos} - \sum \text{Cuotas de Deudas con (es\_gasto\_fijo = 1 y estado activo)}$$
   - El saldo líquido en caja (`saldo_acumulado`) continuará reflejando la contabilidad real diaria de entradas y salidas:
     $$\text{Saldo Acumulado} = \text{Saldo Inicial} + \sum \text{Ingresos Reales} - \sum \text{Gastos Reales}$$
   - Erradicación definitiva de cualquier deducción de gastos diarios operativos dentro de la fórmula de `margen_libre`.

2. **Atributo Booleano `es_gasto_fijo` en Obligaciones:**
   - Incorporación del campo `Es_Gasto_Fijo` (tipo `bool` / `int` 1 o 0) en el esquema de `Obligaciones_Maestro`.
   - Soporte en los DTOs de Pydantic (`ObligacionCreate`, `ObligacionUpdate`, `ObligacionResponse`).
   - Comportamiento reactivo al pausar: Si una obligación se pausa (`Estado == "Pausado"`), `es_gasto_fijo` se desactiva (`0` / `False`), excluyendo su cuota de la deducción del margen libre. Al reactivarse (`Estado == "Activo"`), se restablece su estado booleano configurado.

3. **Manejo de Fallbacks Seguros:**
   - Si `Presupuesto_Base` no tiene ingresos registrados, el fallback debe usar el último salario del Libro Diario o el salario base de referencia, pero **nunca** restar gastos operativos variables.

---

## 3. Fuera de Alcance (No-Scope)

- Modificaciones en la base de datos local SQLite de asistencia laboral (el cambio aplica al dominio financiero y hojas de cálculo contables).
- Alteraciones en la lógica tributaria de IVA o liquidación DNIT.
- Migraciones masivas destructivas en hojas de terceros; se mantiene compatibilidad hacia atrás mediante valores por defecto (`default=True` para obligaciones activas existentes).

---

## 4. Casos de Uso y Criterios de Aceptación

### Caso de Uso 1: Consulta del Dashboard con Margen Libre Impecable
- **Dado** un usuario con Saldo Base de ₲ 6.500.000, Gastos Fijos de ₲ 2.850.000 y Cuotas Fijas Activas de ₲ 1.100.000.
- **Cuando** registra un gasto diario de ₲ 50.000 en el Libro Diario.
- **Entonces:**
  - El `saldo_acumulado` se reduce en ₲ 50.000.
  - El `margen_libre` permanece constante en ₲ 2.550.000 ($6.500.000 - 2.850.000 - 1.100.000$).

### Caso de Uso 2: Pausa de Obligación y Liberación Inmediata de Margen
- **Dado** una deuda activa con cuota de ₲ 300.000 y `es_gasto_fijo = True`.
- **Cuando** el usuario pausa la deuda (`PATCH /obligaciones/{id}` con `estado="Pausado"`).
- **Entonces:**
  - El campo `Es_Gasto_Fijo` pasa a `0` (o se desactiva su cómputo).
  - El `margen_libre` aumenta inmediatamente en ₲ 300.000 en la siguiente consulta de dashboard y simulación.
