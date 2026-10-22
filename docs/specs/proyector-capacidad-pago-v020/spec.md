# Especificación Funcional (Spec) — Versión v0.2.0
## Módulo: Proyector de Capacidad de Pago, Pausado de Deudas, Historial de Cierres y Timeline de Vencimientos

- **Fecha:** 20 de Octubre de 2026
- **Versión de Especificación:** 2.0.0
- **Fase SDD:** 0 (Especificación y Arquitectura)
- **Estado:** Listo para revisión y handoff de backend

---

## 1. Alcance y Objetivos

Evolucionar el módulo financiero de `GammaMobile` desde un listado pasivo y un simulador de cuotas aisladas hacia un ecosistema de **gestión proactiva de tesorería y desendeudamiento**, incorporando las características probadas de `Gamma_bot` (Telegram) y una nueva herramienta de proyección de capacidad de pago mensual.

### Casos de Uso del Alcance (Scope)

#### UC-1: Proyector de Capacidad de Pago del Mes Actual
- **Actor:** Usuario de GammaMobile.
- **Flujo:**
  1. El usuario accede a la pestaña de simulación o herramienta de proyección.
  2. La app presenta el diagnóstico del mes en curso: Total de compromisos de deuda a pagar este mes vs. Fondo disponible (Saldo de caja + Ingresos del mes - Presupuesto base de gastos fijos).
  3. Muestra un semáforo de viabilidad financiera:
     - 🟢 **Superávit:** El margen cubre el 100% de las obligaciones del mes con holgura.
     - 🟡 **Ajustado:** Las cuotas se cubren, pero el buffer de liquidez remanente es inferior al 15%.
     - 🔴 **Déficit:** El dinero disponible no cubre la totalidad de cuotas (destaca cuotas en riesgo de mora).
  4. Permite simular escenarios (*What-If*): ajustar abonos adicionales a ciertas cuotas y observar la reducción de meses de deuda en tiempo real.

#### UC-2: Pausar y Reanudar Obligaciones
- **Actor:** Usuario de GammaMobile.
- **Flujo:**
  1. Desde la tarjeta de una obligación activa, el usuario puede accionar *"Pausar este mes"*.
  2. La deuda pasa a estado `Pausada`. Su cuota mensual se excluye automáticamente de la suma de compromisos del mes actual y del cálculo del Margen Libre Disponible.
  3. El usuario puede filtrar y consultar sus deudas `Pausadas` de forma aislada y reactivarlas en cualquier momento con *"Reanudar"*.

#### UC-3: Historial y Descarga de Cierres Contables y Laborales
- **Actor:** Usuario de GammaMobile.
- **Flujo:**
  1. El usuario navega a la nueva sección **Historial de Cierres**.
  2. Observa el listado cronológico de cierres mensuales (contables y laborales) agrupados por período (`Octubre 2026`, etc.).
  3. Puede presionar *"Ver / Descargar PDF Oficial"* para abrir el comprobante compilado en ReportLab con el visor de PDF nativo o compartirlo.

#### UC-4: Cronograma Mensual de Vencimientos (Timeline)
- **Actor:** Usuario de GammaMobile.
- **Flujo:**
  1. La app presenta una vista de agenda/timeline de los vencimientos del mes, ordenada por día (`dia_vencimiento`).
  2. Destaca visualmente qué deudas ya vencieron en el mes y cuáles están próximas a vencer en los siguientes 7 días.

#### UC-5: Recomendación de Deuda Foco (Bola de Nieve vs Avalancha)
- **Actor:** Usuario de GammaMobile.
- **Flujo:**
  1. El usuario selecciona su preferencia estratégica: **Bola de Nieve** (liquidar menor saldo) o **Avalancha** (liquidar mayor costo).
  2. La app resalta la **Deuda Foco** del mes, aconsejando destinar a esa obligación cualquier excedente de liquidez disponible.

---

## 2. Lo que queda Excluido (No-Scope)
- No se modificará la pasarela de autenticación con Google ni se integrarán bancos externos.
- No se alterarán los scripts de cálculo de nómina fuera de la consulta de los PDFs de cierre ya generados.
- Todo desarrollo de endpoints backend se realizará exclusivamente en la sesión dedicada del repositorio `Gamma_bot`.
