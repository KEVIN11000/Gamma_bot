# Feature Specification: Parser Conversacional de Lenguaje Natural, Rate-Limiting Webhooks y Extensiones UI para Gamma Mobile (v2.0.0 Fase 4)

**Feature Branch**: `Main-stable`  
**Created**: 2026-11-03  
**Status**: Planificación (Fase 0 - SDD)  
**Input**: Requerimientos de HANDOFF.md v2.0.0 Fase 4: Parser conversacional financiero, hardening/rate-limiting en webhooks y diseño de componentes UI para Gamma Mobile.

---

## 1. Alcance y Contexto del Negocio

En las Fases 1, 2 y 3 se consolidó la arquitectura hexagonal, la cola agnóstica multi-canal y el adaptador saliente/entrante de WhatsApp conectado a `cola.db`. En esta **Fase 4**, completamos el ciclo de interacción end-to-end:

1. **Parser Conversacional de Lenguaje Natural (NLP Financiero):** Permitir a los usuarios reportar gastos e ingresos enviando un simple mensaje de texto informal desde WhatsApp (o Telegram / Gamma Mobile), extrayendo automáticamente el tipo (Gasto/Ingreso), monto, categoría, comercio/proveedor y descripción sin necesidad de comandos rígidos.
2. **Hardening y Rate-Limiting en Webhooks:** Blindar el endpoint `POST /api/v1/webhooks/whatsapp` y rutas públicas de la API v1 frente a ráfagas maliciosas o bucles de eventos, protegiendo el worker WSGI de PythonAnywhere mediante limitación de tasa (HTTP 429) y validación estricta de tamaño de payload.
3. **Contratos y Diseño de Componentes UI para Gamma Mobile:** Definir los contratos de interfaz y especificación ergonómica para los nuevos widgets móviles: Tarjeta de Clima con recomendación operativa (`GET /api/v1/clima`) y Widget de Marcación Rápida con retroalimentación háptica y estado offline/online.

---

## 2. Casos de Uso y Escenarios de Aceptación

### Caso de Uso 1: Registro Conversacional de Gastos e Ingresos vía WhatsApp (P1 - Core)
- **Actor:** Usuario autenticado en WhatsApp enviando un mensaje libre.
- **Flujo Principal:**
  1. El usuario envía: `"Gasto 45.000 almuerzo en Don Vito"` o `"gasté 15k en biggie pan y leche"`.
  2. El webhook encola el mensaje y el worker SQLite ejecuta `procesar_mensaje_whatsapp`.
  3. El worker invoca `FinanceNLParser.parse(text)`.
  4. El parser detecta determinísticamente:
     - `tipo_movimiento`: "Gasto"
     - `monto`: 45000 (o 15000)
     - `categoria`: "Comida" (o "Supermercado")
     - `proveedor_cliente`: "Don Vito" (o "Biggie")
     - `descripcion`: "Almuerzo en Don Vito"
     - `confianza`: >= 0.85
  5. El worker persiste el movimiento en Google Sheets / repositorio contable.
  6. El worker despacha vía `whatsapp` una confirmación formateada con emojis:
     ```text
     ✅ *Gasto Registrado*
     💰 Monto: 45.000 Gs
     🏷️ Categoría: Comida
     🏢 Comercio: Don Vito
     ```

### Caso de Uso 2: Fallback Inteligente o Solicitud de Aclaración (P2)
- **Actor:** Usuario enviando un mensaje ambiguo o no financiero.
- **Flujo:**
  - Si el mensaje es un saludo o texto general (`"Hola"`, `"Buenas tardes"`): Responde con menú de ayuda y ejemplos de uso.
  - Si el parser detecta intención de gasto/ingreso pero el monto es dudoso (confianza < 0.60): Si `GEMINI_API_KEY` está activa, consulta a `AIService.procesar_movimiento_con_ia()`. Si aún es ambiguo, solicita amablemente confirmación: `"🤔 Entendí que registraste un gasto, pero no pude determinar el monto exacto. Ej: 'Gasto 50000 combustible en Shell'"`.

### Caso de Uso 3: Endpoint REST de Parsing para Clientes Móviles (P2)
- **Actor:** App móvil Gamma Mobile.
- **Flujo:** `POST /api/v1/movimientos/parse` recibe `{"texto": "..."}`, aplica el parser y devuelve la estructura normalizada en JSON antes de someter la transacción.

### Caso de Uso 4: Hardening y Rate-Limiting en `POST /api/v1/webhooks/whatsapp` (P1 - Seguridad)
- **Actor:** Servidor externo / atacante enviando ráfagas.
- **Criterio:**
  - Si se exceden 60 peticiones/minuto desde la misma IP o instancia, la API responde inmediatamente `HTTP 429 Too Many Requests` sin procesar el body ni tocar la base de datos SQLite.
  - Si el secret `X-Webhook-Secret` o parámetro `secret` no coincide con timing seguro, retorna `HTTP 401 Unauthorized`.

### Caso de Uso 5: Componentes UI Gamma Mobile (Tarjeta de Clima y Marcación Rápida) (P3 - UX)
- **Actor:** Usuario abriendo Gamma Mobile en su dispositivo Android.
- **Criterio:**
  - Widget de clima muestra temperatura actual, condición, icono visual y mensaje de viabilidad operativa ("Apto para trabajo en exterior" / "Precaución por lluvia").
  - Botón táctil de marcación rápida con área táctil >= 56dp x 56dp, estado dinámico (Entrada registrada vs Salida registrada) y protección contra doble pulsación (debounce 1500ms).

---

## 3. Entradas y Salidas Exactas

### `POST /api/v1/movimientos/parse`
- **Request Headers:** `X-API-KEY: <key>`, `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "texto": "Gasto 50.000 combustible en Petrobras"
  }
  ```
- **Response 200 OK:**
  ```json
  {
    "valido": true,
    "tipo_movimiento": "Gasto",
    "monto": 50000.0,
    "categoria": "Combustible",
    "proveedor_cliente": "Petrobras",
    "descripcion": "Combustible en Petrobras",
    "confianza": 0.95
  }
  ```

---

## 4. No-Scope (Lo que queda EXCLUIDO)
- ❌ Modificación de contratos de base de datos de `cola.db` (la migración agnóstica ya soporta `channel` y `recipient_id`).
- ❌ Modelos de Deep Learning entrenados localmente (el parser utilizará regex determinista y compilada de alto rendimiento + fallback opcional a Gemini).
- ❌ Pasarelas de pago bancarias directas (el bot registra transacciones contables, no ejecuta transferencias bancarias).
