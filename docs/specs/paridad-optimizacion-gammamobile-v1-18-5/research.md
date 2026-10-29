# Research: Estrategia de Paridad y Optimización con Gamma Mobile

## Decisiones Técnicas

### 1. Compatibilidad Dual de Alias en Pydantic (`MovimientoCreate`)
- **Decisión:** Configurar `movimiento: TipoMovimiento = Field(default=TipoMovimiento.GASTO, alias="tipo")` y habilitar `populate_by_name = True` (o `allow_population_by_field_name = True` según versión de Pydantic v1/v2).
- **Por qué:** Permite que clientes legados que envían `"movimiento"` y la app móvil que envía `"tipo"` funcionen sin romper contratos ni requerir bifurcaciones en endpoints.
- **Alternativas descartadas:** Mantener solo `"movimiento"` y obligar a parchar la app móvil (rompe releases en producción de Android).

### 2. Idempotencia de Movimientos (`client_id`)
- **Decisión:** Utilizar una caché en memoria / almacén temporal de IDs procesados con TTL de 24 horas (`_PROCESSED_CLIENT_IDS = {}`) o persistencia ligera en `data/idempotency.json`.
- **Por qué:** Evita que ante cortes de conexión o reintentos automáticos del WorkManager de Android se inserten filas duplicadas en el Libro Diario.
- **Alternativas descartadas:** Confiar únicamente en la sincronización del cliente.

### 3. Respuestas Informativas en Marcaciones Laborales
- **Decisión:** Detectar respuestas informativas de `AgenteAutonomoHoras` (ej. textos que inician con `"ℹ️"` o contienen `"Ya registraste tu entrada"`) y devolver `200 OK` con metadata estructurada `{"tipo": "info", "mensaje": ..., "confirmado_en_planilla": True}` en vez de `400 Bad Request`.
- **Por qué:** La app móvil interpreta cualquier código 4xx como error fatal en el Snackbar; un 200 con flag informativo permite notificar amigablemente sin alarmar al usuario.
- **Alternativas descartadas:** Seguir devolviendo 400 y obligar a parsear el cuerpo del error en Android.

### 4. Precisión en Analíticas Laborales MTD
- **Decisión:** Condicionar el cómputo de horas trabajadas y salario devengado a que la fila contenga tanto marcación de entrada como marcación de salida (`salida` no vacía).
- **Por qué:** Días en curso con solo entrada distorsionaban el devengado diario y acumulado proyectando jornadas completas antes de tiempo.
