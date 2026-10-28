# Plan de Arquitectura y Diseño Técnico: Remediación Cierre Drive Backup y Soporte (v1.18.3)

## 1. Arquitectura Modular

```
[ Telegram / Cron ]
         │
         ▼
[ src/logic/financiero.py ] ──► ejecutar_cierre_mensual()
         │                               │
         │ (1. Genera CSV temporal)     │ (2. Delega backup)
         ▼                               ▼
    [ tempfile ]            [ src/services/drive_service.py ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
      ¿Google Drive API disponible?                    ¿Error / Offline?
                 │                                               │
           [ Sí: Subir ]                                  [ Fallback local ]
                 │                                               │
         Retorna file_id                               Retorna local:<path>
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                   Persistir en 'Cierres_Historicos'
                                         ▼
                      Resetear 'Libro_Diario'
```

---

## 2. Contratos y Manejo de Errores

### 2.1 `DriveService.upload_backup(file_path: str, destination_folder_id: Optional[str] = None) -> str`
- **Entrada:** Ruta al archivo temporal generado (`str`).
- **Salida:** `str` (ID de Google Drive o `local:<filename>` en caso de fallback).
- **Flujo:**
  1. Intentar instanciar el cliente de Google Drive (`googleapiclient.discovery.build('drive', 'v3', credentials=credentials)`).
  2. Si `credentials.json` no existe, no tiene scope de Drive, o la llamada a la API arroja una excepción (`HttpError`, timeout, etc.):
     - Registrar un `warning` explícito en `logger`.
     - Copiar el archivo temporal a `BASE_DIR / "data" / "backups" / Path(file_path).name`.
     - Retornar `f"local:{Path(file_path).name}"`.
  3. Si la subida a Drive es exitosa:
     - Retornar el `id` asignado por Google Drive.

### 2.2 `ejecutar_cierre_mensual` en `src/logic/financiero.py`
- Valida que `drive_id` no sea nulo o vacío (`if not drive_id: raise RuntimeError(...)`).
- Como `DriveService.upload_backup` siempre retornará o el `file_id` de Google Drive o el prefijo `local:<nombre>`, la guarda solo se activará si ocurre un fallo catastrófico de sistema (ej. sin espacio en disco para el backup local).
- Se preserva la columna `Archivo_Backup_Drive` en `Cierres_Historicos`, guardando el ID de Drive o la referencia local para auditoría.

### 2.3 Corrección en `src/com/handlers/soporte.py`
- Modificar:
  ```python
  # ANTES (generaba /src/src/data/tickets.json):
  UNIFIED_TICKETS_FILE = BASE_DIR / "src" / "data" / "tickets.json"

  # DESPUÉS:
  UNIFIED_TICKETS_FILE = BASE_DIR / "data" / "tickets.json"
  ```
- Asegurar que el directorio contenedor `UNIFIED_TICKETS_FILE.parent` exista antes de escribir (`mkdir(parents=True, exist_ok=True)`).

---

## 3. Estrategia de Testing

1. **`tests/test_services.py`:**
   - Test `test_drive_upload_backup_fallback_local`: verifica que si no hay credenciales o Drive falla, se copie el archivo a `data/backups/` y retorne `local:...`.
   - Test `test_drive_upload_backup_success_mock`: simula respuesta válida de Google Drive API y verifica retorno del `id`.
2. **`tests/test_financiero.py`:**
   - Test `test_ejecutar_cierre_mensual_con_fallback_local`: verifica que el cierre mensual se registre exitosamente en Sheets incluso cuando el backup sea local.
3. **`tests/test_soporte.py`:**
   - Test `test_soporte_unified_tickets_file_path`: verifica que `UNIFIED_TICKETS_FILE` apunte a `src/data/tickets.json` existente y no genere ruta anidada `src/src/data`.

---

## 4. Gestión de Versión
- Versión bump: de `1.18.2` a `1.18.3` (patch).
- Archivos a actualizar: `VERSION`, `CHANGELOG.md`, `README.md`, `src/api/blueprint.py` (en endpoint `/health`).
