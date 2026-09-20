# Tasklist: Estabilización de Suite de Pruebas (v1.13.0)

Esta lista detalla las tareas necesarias para reparar los 6 tests rotos reportados en el `HANDOFF.md` tras las últimas refactorizaciones de seguridad y esquema contable.

## Fase 1: Correcciones en la capa de Seguridad
- [x] **1. `test_auth_security.py`**:
  - *Problema*: La prueba `test_deploy_403_without_webhook_secret_production` asume que la app arranca y retorna `403`. Sin embargo, con el nuevo `validate_production_config()`, la app lanza `RuntimeError` en arranque si faltan secretos.
  - *Solución*: Modificar la aserción de la prueba para interceptar explícitamente y validar la ocurrencia del `RuntimeError`.

## Fase 2: Correcciones en Mocks de Integración y Servicios
- [x] **2. `test_integration_local.py`**:
  - *Problema*: Tras sustituir la inserción de datos por la directiva `append_row()`, el mock `FakeWorksheet` crashea al recibir el kwarg `value_input_option` propio de la API real de gspread.
  - *Solución*: Extender la firma de `FakeWorksheet.append_row(self, row: list, **kwargs)` para absorber el parámetro en el entorno local de test.
- [x] **3. `test_services.py`**:
  - *Problema*: Las pruebas asumen que los métodos de `CalendarService` y `DriveService` devuelven identificadores dummy (`"mock_event_id_Test"`, etc.). Ahora devuelven estáticamente `""` o `False` para no enviar mensajes engañosos al logger.
  - *Solución*: Actualizar las aserciones de `test_calendar_create_event`, `test_calendar_mark_completed` y `test_drive_upload_backup` a sus valores reales `""` y `False`.

## Fase 3: Correcciones en Lógica de Repositorio
- [x] **4. `test_sheets_repository.py`**:
  - *Problema*: La prueba `test_get_movimientos_mes` provee un diccionario falso con `"Fecha": "2023-05-15"`, pero la implementación productiva espera formato con barras `15/05/2023` o el campo de 16-cols `"Mes": "05/2023"`.
  - *Solución*: Actualizar el mock del test a `[{"Fecha": "15/05/2023", "Mes": "05/2023"}]` para que retorne concordancia válida.

## Fase 4: Validación y Cierre
- [x] **5. QA Final**:
  - Ejecutar `pytest tests/ -q` y confirmar 101 tests pasados (100%).
  - Actualizar el `HANDOFF.md` reflejando el éxito de esta estabilización.
