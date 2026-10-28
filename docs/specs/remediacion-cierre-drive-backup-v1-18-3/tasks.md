# Checklist de Tareas (Tasks) — Remediación Cierre Drive Backup y Soporte (v1.18.3)

- [x] 1. **Corrección de ruta en soporte**: Ajustar `UNIFIED_TICKETS_FILE` en `src/com/handlers/soporte.py` para eliminar la duplicación de `src/` (`BASE_DIR / "data" / "tickets.json"`).
- [x] 2. **Implementación de `DriveService.upload_backup`**: Desarrollar la subida con Google Drive API v3 y fallback determinista local en `src/services/drive_service.py`.
- [x] 3. **Resiliencia en `ejecutar_cierre_mensual`**: Asegurar en `src/logic/financiero.py` la persistencia correcta del identificador retornado (Drive o local) y manejo sin abortos indebidos.
- [x] 4. **Pruebas unitarias de servicios y soporte**: Actualizar y expandir `tests/test_services.py`, `tests/test_financiero.py` y `tests/test_soporte.py` para cubrir los nuevos flujos de backup y rutas.
- [x] 5. **Actualización de versión y release**: Bump de versión a `1.18.3` en `VERSION`, `src/api/blueprint.py`, `CHANGELOG.md` y `README.md`.
- [x] 6. **Certificación de calidad y Linters**: Ejecutar y validar `black`, `flake8`, `mypy` y la suite de `pytest` (219+ tests).
