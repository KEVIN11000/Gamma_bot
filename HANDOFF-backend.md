# Traspaso Backend (Gamma Mobile -> Gamma_bot)
## Requerimientos de Backend para Estabilidad y Paridad con Gamma Mobile

- **Fecha:** 29 de Octubre de 2026
- **Origen:** Gamma Mobile (Sesión de Remediación y Estabilidad `v0.0.12` / `remediacion-estabilidad-v012`)
- **Destino:** Repositorio `Gamma_bot` (`E:\PG\vcp-s\Gamma_bot`) para desarrollo en su sesión dedicada.
- **Principio:** Cero modificaciones en el backend durante la sesión de la app móvil; todos los requerimientos del servidor quedan formalizados en este documento.

---

### Módulo 1: Alineación de Contratos y Esquemas (Pydantic vs Mobile)

1. **Soporte de Alias `"tipo"` en `POST /api/v1/movimientos` (`src/api/schemas.py`)**:
   - **Problema:** Android envía `"tipo": "Ingreso"`. `MovimientoCreate` solo reconoce `"movimiento"`, descartando `"tipo"` y asignando `TipoMovimiento.GASTO` por defecto. En consecuencia, todos los ingresos móviles se registran como gastos en Google Sheets.
   - **Solución Requerida:** En `src/api/schemas.py`, configurar en `MovimientoCreate`:
     ```python
     movimiento: TipoMovimiento = Field(default=TipoMovimiento.GASTO, alias="tipo")
     ```
     O permitir tanto `tipo` como `movimiento` en el validador antes de crear la fila.

2. **Desempaquetado de `deuda_foco` en `GET /api/v1/obligaciones/foco` (`src/api/blueprint.py`)**:
   - **Problema:** El endpoint devuelve `{"criterio": "...", "deuda_foco": {...}}`, mientras que la app móvil consumía el DTO plano esperando los campos en la raíz.
   - **Solución Requerida:** Mantener el objeto `deuda_foco` o exponer los campos planos en la raíz para garantizar compatibilidad con versiones previas.

3. **Paridad de Clave en IA y OCR (`src/logic/ai_service.py`)**:
   - **Problema:** El servicio de IA retorna `"tipo_movimiento"`, mientras que la app móvil consume `"tipo"`.
   - **Solución Requerida:** Retornar ambas claves (`datos["tipo"] = tipo` y `datos["tipo_movimiento"] = tipo`) en la respuesta JSON.

---

### Módulo 2: Respuestas Informativas y Códigos HTTP

1. **Marcación Laboral Informativa en `POST /api/v1/asistencia/marcar` (`src/api/blueprint.py`)**:
   - **Problema:** Cuando `AgenteAutonomoHoras` retorna `"ℹ️ Ya registraste tu entrada hoy"`, el endpoint devuelve `HTTP 400 Bad Request`, provocando que la app móvil muestre una alerta de error crítico.
   - **Solución Requerida:** Responder con `HTTP 200 OK` y payload estructurado:
     ```json
     {
       "tipo": "info",
       "mensaje": "ℹ️ Ya registraste tu entrada hoy a las HH:mm",
       "confirmado_en_planilla": true
     }
     ```

2. **Invalidación Reactiva de Caché (`src/repositories/sheets_repository.py`)**:
   - **Problema:** `_sheets_cache` tiene un TTL de 180 segundos. Tras registrar transacciones desde la app, `GET /dashboard/summary` sigue retornando el balance antiguo durante 3 minutos.
   - **Solución Requerida:** Llamar a `_sheets_cache.clear()` al insertar movimientos en `POST /api/v1/movimientos`.

3. **Cálculo de Analíticas MTD y Devengado Laboral (`src/logic/logic.py`)**:
   - **Problema:** El devengado de horas y salario computa días con sólo marcación de entrada como si fueran jornadas completas.
   - **Solución Requerida:** En `AgenteAutonomoHoras.obtener_analiticas_horas()`, condicionar el cálculo de horas trabajadas y salario devengado acumulado a que el día tenga registrada su salida efectiva.

---

### Módulo 3: Ejecución Real de Cierres Contables

1. **Reemplazo de Stub en `POST /api/v1/cierres/ejecutar` (`src/api/blueprint.py`)**:
   - **Problema:** El endpoint genera un PDF sintético con ReportLab hardcodeando 160h y 4.5M Gs sin interactuar con Google Sheets ni ejecutar `execute_monthly_closing()`.
   - **Solución Requerida:** Integrar la llamada real a `agente_excel.ejecutar_cierre_periodo_manual()` o `execute_monthly_closing()`.

2. **Sincronización de Cierres Laborales en Historial (`src/api/blueprint.py`)**:
   - **Problema:** No existe un endpoint que liste los cierres laborales archivados en Google Sheets para que la app móvil los consulte.
   - **Solución Requerida:** Implementar `GET /api/v1/asistencia/cierres` retornando la lista de períodos laborales cerrados y sus PDFs.

---

### Módulo 4: Deduplicación e Idempotencia

1. **Recepción de `clientId` o `id` en `POST /api/v1/movimientos` (`src/api/blueprint.py`)**:
   - **Problema:** Si ocurre un timeout de red tras escribir en Google Sheets, el Worker de Android reintenta y duplica el asiento contable en la planilla.
   - **Solución Requerida:** Verificar si el `client_id` recibido en el header `X-Client-Id` o en el cuerpo ya fue registrado en las últimas 24 horas antes de hacer `append_row()`.
