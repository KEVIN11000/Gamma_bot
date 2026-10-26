# Requerimientos Técnicos para el Backend Core (`Gamma_bot`)
## Módulo: Saneamiento de Almacén de Tickets, Blindaje de Telemetría Vigía y Aislamiento de Tests en CI

- **Fecha:** 26 de Octubre de 2026
- **Destino:** Repositorio `Gamma_bot` (`E:\PG\vcp-s\Gamma_bot`) para su desarrollo y ejecución en sesión dedicada.
- **Aislamiento:** Este documento especifica con exactitud quirúrgica las correcciones y verificaciones requeridas en el backend sin modificar código de `Gamma_bot` desde este workspace móvil.

---

## 1. Contexto y Diagnóstico del Problema

Durante la auditoría de inicio de fase del ecosistema móvil y la revisión de la pantalla `SistemaScreen` (sección de Tickets de Soporte), se detectó que el endpoint `GET /api/v1/soporte/tickets` entregaba una lista sobrecargada con **70 tickets**, de los cuales **59 figuraban en estado `Abierto`** con el asunto recurrente `"Fallo sincronización"` y descripción `"Error al conectar con servidor"`.

### Causa Raíz Identificada
1. **Falta de Fixture / Mock en Pruebas Unitarias de la API:**
   En `tests/test_mobile_api.py`, la prueba `test_soporte_tickets_and_logs` aísla correctamente el archivo mediante `monkeypatch.setattr("api.blueprint.TICKETS_FILE", fake_tickets)`.
   Sin embargo, en el test subsiguiente `test_github_sync_resilience_and_circuit_breaker` (línea ~1000 en `tests/test_mobile_api.py`):
   ```python
   # 1. Crear ticket y verificar dispatch hacia GitHub
   res_post = client.post(
       "/api/v1/soporte/tickets",
       headers=headers,
       json={
           "asunto": "Fallo sincronización",
           "descripcion": "Error al conectar con servidor",
           "origen": "app",
       },
   )
   ```
   **No se aplicó `monkeypatch` a `api.blueprint.TICKETS_FILE` ni a `src/data/tickets.json`.**
   Como consecuencia, cada corrida local o remota de `pytest` realizó operaciones reales de escritura (`POST` e inserción en cabeza de lista) y mutación (`PATCH` a `"Abierto"`) directamente sobre el archivo productivo `src/data/tickets.json`.
2. **Impacto en el Cliente Móvil (`GammaMobile`):**
   Al consultar `GET /api/v1/soporte/tickets`, la aplicación móvil recibe 59 incidencias abiertas ficticias, distorsionando las estadísticas de soporte y el filtro de tickets del usuario.

---

## 2. Requerimientos de Implementación en `Gamma_bot`

### Requerimiento 1: Saneamiento del Archivo `src/data/tickets.json`
- **Archivo:** `src/data/tickets.json`
- **Acción:**
  Purgar la totalidad de registros espurios de prueba generados por `pytest` (`TCK-007` al `TCK-078`), restaurando el archivo únicamente con los **6 tickets legítimos y resueltos** del historial del proyecto:
  - `TCK-001`: *"Configuración de Conexión y API Key en Android"* (`Cerrado`)
  - `TCK-002`: *"Desalineación de esquemas en Libro Diario y Obligaciones"* (`Cerrado`)
  - `TCK-003`: *"Sincronización salarial Libro Diario hacia Presupuesto Base"* (`Cerrado`)
  - `TCK-004`: *"Errores en el cierre mensual y la marcación de materias"* (`Cerrado`)
  - `TCK-005`: *"Fallo en cierre mensual de ingresos y egresos contables"* (`Cerrado`)
  - `TCK-006`: *"Despliegue y recarga de worker en PythonAnywhere"* (`Cerrado`)

### Requerimiento 2: Blindaje y Aislamiento de `test_mobile_api.py`
- **Archivo:** `tests/test_mobile_api.py`
- **Acción:**
  En la prueba `test_soporte_tickets_github_sync_dispatch`, inyectar los fixtures `tmp_path` y `monkeypatch`, asegurando que `api.blueprint.TICKETS_FILE` apunte a un archivo efímero durante toda la ejecución del test:
  ```python
  def test_soporte_tickets_github_sync_dispatch(client, monkeypatch, tmp_path):
      headers = {"X-API-KEY": "test-secret-key"}
      fake_tickets = tmp_path / "tickets.json"
      fake_tickets.write_text("[]", encoding="utf-8")
      monkeypatch.setattr("api.blueprint.TICKETS_FILE", fake_tickets)
  ```
  *Nota:* Auditar también si alguna otra prueba en `tests/` invoca rutas `/soporte/tickets` sin aislar `TICKETS_FILE`.

### Requerimiento 3: Verificación de Integridad de Telemetría Vigía
- **Archivos:** `src/com/core/telemetry.py` y `src/api/blueprint.py`
- **Acción:**
  - Verificar que `reportar_incidente_vigia()` mantenga activo su mecanismo de *cooldown* anti-spam (30 minutos por firma de error).
  - Comprobar que ante fallos al conectar con la API de GitHub, `reportar_incidente_vigia()` degrade silenciosamente retornando `False` sin interrumpir la creación local del ticket en `tickets.json` ni lanzar excepciones HTTP 500 al cliente móvil.

### Requerimiento 4: Verificación de Endpoint `/health` para Gamma Mobile
- **Archivo:** `src/api/blueprint.py`
- **Acción:**
  - Confirmar que `GET /api/v1/health` retorne en su payload:
    ```json
    {
      "status": "ok",
      "sheets_connected": true,
      "calendar_connected": true,
      "version": "1.18.0",
      "mobile_version": "0.0.10",
      "download_url": "https://github.com/KEVIN11000/Gamma_Mobile/releases/latest"
    }
    ```
  - Asegurar que la URL apunte al repositorio oficial `KEVIN11000/Gamma_Mobile` y no a repositorios obsoletos.

---

## 3. Guía de Ejecución y Pruebas en la Sesión de `Gamma_bot`

Al abrir la sesión en `E:\PG\vcp-s\Gamma_bot`, ejecutar los siguientes pasos de validación:

```bash
# 1. Ejecutar la suite de tests de la API móvil con aislamiento verificado
pytest tests/test_mobile_api.py -v

# 2. Comprobar que el archivo tickets.json NO haya sido modificado por pytest
git status src/data/tickets.json

# 3. Validar sintaxis y formato
flake8 src/api/blueprint.py tests/test_mobile_api.py
```

---

## 4. Criterio de Aceptación (Definición de Terminado)

1. `src/data/tickets.json` contiene estrictamente 6 tickets (`TCK-001` a `TCK-006`) con formato JSON válido e indentado a 2 espacios.
2. `pytest tests/test_mobile_api.py` pasa 100% en verde sin ensuciar ni modificar `src/data/tickets.json`.
3. Al consultar `GET /api/v1/soporte/tickets` desde un cliente autenticado, devuelve una lista de 6 elementos con estados consistentes.
