# Guía de Validación Rápida (Quickstart) — Integración GammaMobile v0.0.9

**Fecha:** 2026-10-20  
**Feature:** `integracion-gammamobile-v009`  
**Objetivo:** Instrucciones ejecutables para validar de extremo a extremo los 5 módulos integrados en `Gamma_bot`.

---

## 1. Prerrequisitos y Entorno

1. Python 3.13 / Anaconda con dependencias del proyecto instaladas.
2. Servidor local iniciado o ejecución contra suite de tests unitarios/integración con mocks de Google APIs.
3. Variable de entorno `MOBILE_API_KEY` configurada o utilizando la clave de pruebas local.

```powershell
$env:MOBILE_API_KEY = "test_key_mobile_123"
```

---

## 2. Escenarios de Validación Ejecutables

### Escenario 1: Marcación Laboral Real (`POST /api/v1/asistencia/marcar`)

#### Caso Exitoso
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/v1/asistencia/marcar" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY; "Content-Type" = "application/json" } `
  -Body '{"modo": "normal"}'
```
* **Respuesta esperada:** HTTP 200 con `tipo` (`"entrada"` o `"salida"`), `hora` (`HH:MM`) y `mensaje` confirmatorio retornado por la lógica de asistencia.

#### Caso Rechazo Semántico (ej. Marcación duplicada)
* **Respuesta esperada:** HTTP 400 o 409 con `tipo: "error"` y `mensaje` descriptivo (`"❌ Ya registraste salida para el día de hoy"`).

---

### Escenario 2: Resumen Financiero y Reactividad (`GET /api/v1/dashboard/summary`)

```powershell
$res = Invoke-WebRequest -Method Get -Uri "http://127.0.0.1:5000/api/v1/dashboard/summary" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY }
$res.Headers["Cache-Control"]
$res.Content | ConvertFrom-Json
```
* **Respuesta esperada:**
  - Cabecera `Cache-Control` contiene `no-store, no-cache`.
  - JSON con `mes`, `ingresos`, `gastos`, `flujo_neto`, `margen_libre` (calculado dinámicamente) y `posicion_iva`.

---

### Escenario 3: CRUD de Avisos con Google Calendar (`/api/v1/avisos`)

#### Crear Aviso con Repetición e Hitos
```powershell
$aviso = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/v1/avisos" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY; "Content-Type" = "application/json" } `
  -Body '{"titulo": "Pago Cuota Préstamo", "fecha_evento": "25/10/2026 10:00", "repeticion": "MENSUAL", "hitos_minutos": [1440, 180, 60]}'
$avisoId = $aviso.id
```
* **Respuesta esperada:** HTTP 201 con objeto que contiene `id`, `titulo`, `repeticion` e `hitos_minutos`.

#### Actualizar Aviso Existente
```powershell
Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:5000/api/v1/avisos/$avisoId" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY; "Content-Type" = "application/json" } `
  -Body '{"titulo": "Pago Cuota Préstamo - Reprogramado", "fecha_evento": "26/10/2026 10:00"}'
```
* **Respuesta esperada:** HTTP 200 con título y fecha actualizados en persistencia y Calendar.

#### Eliminar Aviso
```powershell
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:5000/api/v1/avisos/$avisoId" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY }
```
* **Respuesta esperada:** HTTP 200 con confirmación de eliminación.

---

### Escenario 4: Ciclo de Vida de Obligaciones y Simulación Dinámica (`/api/v1/obligaciones`)

#### Crear Deuda en Estado Simulado
```powershell
$obl = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/v1/obligaciones" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY; "Content-Type" = "application/json" } `
  -Body '{"entidad": "Banco Itaú", "nombre": "Crédito Automotor", "monto_inicial": 15000000, "cuotas_totales": 24, "cuotas_restantes": 24, "cuota_referencia_gs": 850000, "dia_vencimiento": 15, "estado": "Simulado"}'
$oblId = $obl.ID_Obligacion
```
* **Respuesta esperada:** HTTP 201 con `Estado: "Simulado"` persistido en Sheets.

#### Aprobar Simulación (Transición a Activo)
```powershell
Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:5000/api/v1/obligaciones/$oblId" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY; "Content-Type" = "application/json" } `
  -Body '{"estado": "Activo"}'
```
* **Respuesta esperada:** HTTP 200 con `Estado: "Activo"`.

#### Descartar/Eliminar Obligación
```powershell
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:5000/api/v1/obligaciones/$oblId" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY }
```
* **Respuesta esperada:** HTTP 200 con confirmación de borrado en `Obligaciones_Maestro`.

#### Simulación con Margen Libre Real
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/v1/obligaciones/simular" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY; "Content-Type" = "application/json" } `
  -Body '{"monto": 5000000, "meses": 10}'
```
* **Respuesta esperada:** HTTP 200 con `margen_actual` calculado desde `calcular_margen_de_ataque()` (no 2.000.000 hardcodeado).

---

### Escenario 5: Consulta de Logs en Vivo (`GET /api/v1/sistema/logs`)

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:5000/api/v1/sistema/logs?limit=10" `
  -Headers @{ "X-API-KEY" = $env:MOBILE_API_KEY }
```
* **Respuesta esperada:** Array JSON de hasta 10 entradas ordenadas cronológicamente de la más reciente a la más antigua, con campos `timestamp`, `nivel` y `mensaje`.

---

## 3. Comandos de Validación Automatizada (Tests)

```powershell
& "D:\Program Files\Anaconda\python.exe" -m pytest tests/test_mobile_api.py -v
& "D:\Program Files\Anaconda\python.exe" -m black --check src tests/test_mobile_api.py
& "D:\Program Files\Anaconda\python.exe" -m flake8 src/api/blueprint.py src/api/schemas.py tests/test_mobile_api.py
& "D:\Program Files\Anaconda\python.exe" -m mypy src/api/blueprint.py src/api/schemas.py
```
