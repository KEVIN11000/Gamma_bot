# Feature Specification: Proyector de Flujo de Caja, Alertas Presupuestarias Multi-Canal y Notificaciones Push (v2.0.0 Fase 5)

**Feature Branch**: `Main-stable`  
**Created**: 2026-11-03  
**Status**: Planificación (Fase 0 - SDD)  
**Input**: Requerimientos v2.0.0 Fase 5: Proyección de flujo de caja a 30 días, alertas presupuestarias automáticas proactivas y adaptador de notificaciones push para Gamma Mobile.

---

## 1. Alcance y Contexto del Negocio

Con la infraestructura multi-canal (Telegram, WhatsApp), el despachador unificado, la cola asíncrona y el parser conversacional de transacciones ya consolidados, la **Fase 5** añade inteligencia predictiva y alertas proactivas:

1. **Proyector de Flujo de Caja a 30 Días (`CashFlowProjector`):**
   - Calcula el balance esperado día a día para los próximos 30 días calendario.
   - Computa ingresos esperados (sueldo base registrado en `Presupuesto_Base` / `LocalRepository`), compromisos fijos y cuotas de obligaciones (hoja `Obligaciones`) y promedios diarios de gastos variables.
   - Detecta si el saldo proyectado caerá por debajo de cero en algún día del horizonte, alertando sobre "días críticos de liquidez".
2. **Endpoint REST `GET /api/v1/proyecciones/flujo-caja`:**
   - Provee a Gamma Mobile y dashboards web un contrato enriquecido con:
     - `saldo_actual`: Monto disponible actual.
     - `saldo_proyectado_fin_periodo`: Saldo estimado al finalizar los 30 días.
     - `ingresos_proyectados`: Total de ingresos estimados.
     - `gastos_fijos_proyectados`: Total de cuotas y servicios fijos a vencer.
     - `gastos_variables_estimados`: Proyección estadística de gastos cotidianos.
     - `dias_criticos`: Lista de días con saldo negativo o inferior al umbral de seguridad.
     - `proyeccion_diaria`: Arreglo de 30 elementos con `fecha`, `saldo_inicio`, `ingresos`, `egresos`, `saldo_fin`.
3. **Alertas Preventivas de Desvío Presupuestario Proactivas Multi-Canal:**
   - Al registrar un gasto (vía WhatsApp, Mobile API o Telegram), si `evaluar_techo_presupuestario` detecta que la categoría superó el umbral configurado (ej. 80% o 100%), encola automáticamente en `cola.db` una notificación enriquecida con emojis.
   - Aplica un **cooldown de 24 horas por categoría** para no enviar alertas repetitivas al usuario si registra múltiples compras seguidas.
4. **Adaptador de Notificaciones Push (`PushNotificationAdapter`):**
   - Implementa `INotificationPort`.
   - Permite enviar notificaciones push a dispositivos Android (Gamma Mobile) registrados.
   - Endpoint `POST /api/v1/dispositivos/registrar` para persistir `device_token`, `plataforma` ("android") y `alias_usuario`.

---

## 2. Casos de Uso y Escenarios de Aceptación

### Caso de Uso 1: Consulta de Flujo de Caja a 30 Días (P1)
- **Actor:** App móvil Gamma Mobile o usuario consultando proyecciones.
- **Flujo:** Llama a `GET /api/v1/proyecciones/flujo-caja` con `X-API-KEY`.
- **Criterio:** Recibe código 200 con el balance proyectado a 30 días, detalle de compromisos fijos ordenados por fecha de vencimiento y lista de días críticos si existen.

### Caso de Uso 2: Emisión Automática de Alerta Presupuestaria al Registrar Gasto (P1)
- **Actor:** Usuario que gasta en una categoría cercana o superior al límite (ej. Supermercado).
- **Flujo:**
  1. El usuario registra un gasto de 300.000 Gs en Supermercado.
  2. El total acumulado en el mes alcanza 85% del presupuesto asignado.
  3. El sistema detecta `alerta_emitida = True` y verifica que no se haya emitido una alerta para "Supermercado" en las últimas 24 horas.
  4. Encola trabajo `enviar_notificacion` con canal preferente (WhatsApp o Telegram).
  5. El usuario recibe el mensaje de alerta proactiva:
     ```text
     ⚠️ *Alerta Presupuestaria: Supermercado*
     Has consumido el 85% de tu presupuesto mensual (1.700.000 / 2.000.000 Gs).
     💡 Te restan 300.000 Gs para el resto del mes.
     ```

### Caso de Uso 3: Registro de Dispositivo Móvil para Push (P2)
- **Actor:** Gamma Mobile al iniciar sesión.
- **Flujo:** Envía `POST /api/v1/dispositivos/registrar` con `{"device_token": "fcm_token_...", "platform": "android"}`.
- **Criterio:** Retorna 200 OK con `{"status": "ok", "registrado": true}` y almacena el token sin duplicados.

---

## 3. No-Scope (Lo que queda EXCLUIDO)
- ❌ Modificación de los encabezados existentes de `Libro_Diario` u `Obligaciones`.
- ❌ Pasarelas de débito automático bancario.
- ❌ Reemplazo de Firebase Cloud Messaging por servidores MQTT propios (se utiliza estándar HTTP/FCM token).
