# Plan de Arquitectura y Diseño Técnico: Remediación SyncService

**Incidente:** `TG-0b665c71`  
**Fecha:** 2026-11-05  
**Estado:** Fase 0 — Diseño Técnico Aprobado

---

## 1. Arquitectura Modular y Aislamiento de Dominios

```
                  ┌────────────────────────────────────────────────────────┐
                  │                      GAMMA BOT                         │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
   [ Dominio Asistencia ]                                          [ Dominio Contabilidad ]
   - Planilla: SPREADSHEET_ID                                      - Planilla: LIBRO_CONTABLE_ID
   - Módulos: AgenteAutonomoHoras, SyncService                     - Módulos: SheetsRepository, AgenteFinanciero
   - Tablas: asistencia_laboral, asistencia_materias               - Tablas: movimientos, obligaciones, presupuestos
```

---

## 2. Contratos y Modificaciones Detalladas

### 2.1. `src/services/sync_service.py`
1. **Inicialización y Aislamiento:**
   ```python
   self.spreadsheet_id = (
       spreadsheet_id
       or os.getenv("SPREADSHEET_ID")
       or ""
   )
   if not self.spreadsheet_id:
       raise ValueError("SPREADSHEET_ID no está configurado para el servicio de asistencia.")
   ```
   *Se remueve toda referencia a `LIBRO_CONTABLE_ID`.*

2. **Resolución de Hoja Laboral:**
   ```python
   def _nombre_hoja_horas(self, mes: int | None = None, anio: int | None = None) -> str:
       ahora = get_now_py()
       m = mes if mes is not None else ahora.month
       y = anio if anio is not None else ahora.year
       # 1. Priorizar periodo_actual.txt si coincide el mes/año o no se pasaron argumentos
       path_txt = Path(__file__).resolve().parents[1] / "periodo_actual.txt"
       if path_txt.exists():
           try:
               contenido = path_txt.read_text(encoding="utf-8").strip()
               if contenido:
                   if mes is None and anio is None:
                       return contenido
                   # Si se especificó mes/año, validar que coincida
                   partes = contenido.split()
                   if len(partes) == 2 and partes[1] == str(y):
                       return contenido
           except Exception:
               pass
       return f"{MESES_ES[m - 1]} {y}"
   ```

3. **Búsqueda Secuencial en Rango 2..40 y Fila Contigua:**
   ```python
   fechas_col = ws.col_values(2)
   fila_encontrada = None
   primera_fila_vacia = None

   for i in range(1, 40):
       fila = i + 1
       if i < len(fechas_col):
           val_iso = self._normalizar_a_iso(fechas_col[i])
           if val_iso == f_iso:
               fila_encontrada = fila
               break
       elif primera_fila_vacia is None:
           primera_fila_vacia = fila
           break

   fila_destino = fila_encontrada or primera_fila_vacia or (len(fechas_col) + 1)
   ```

4. **Escritura Segura con Preservación de Fórmula:**
   - Si la fila es nueva (`fila_encontrada is None`), escribir `A{fila_destino}:B{fila_destino}` con `[[dia, fecha_display]]`.
   - Si la jornada está abierta, insertar fórmula en columna G:
     `=SI(VALOR(D{fila})<>""; (VALOR(D{fila})-VALOR(C{fila}))+(VALOR(F{fila})-VALOR(E{fila})); VALOR(F{fila})-VALOR(C{fila})) * 24`
   - Escribir `C{fila}:F{fila}` con `[[entrada, s_almuerzo, v_almuerzo, salida]]`.
   - Si la jornada está cerrada (`hora_salida` y `horas_decimal > 0`), escribir `horas_decimal` en G o mantener fórmula evaluada.
   - Todo con `value_input_option="USER_ENTERED"`.

5. **Parámetro `forzar: bool = False`:**
   - Permite forzar el volcado de fechas aunque tengan `sincronizado_sheets = 1` (útil para rescate y reconciliación).

### 2.2. `src/com/handlers/soporte.py`
En `handle_soporte_callback`:
```python
try:
    bot.edit_message_text(...)
except Exception as e:
    if "message is not modified" in str(e).lower():
        logger.debug(f"Ignorando mensaje no modificado en soporte: {e}")
    else:
        raise
```

### 2.3. `src/flask_app.py`
En `deploy()`:
Tras completar `git reset --hard` y antes de tocar WSGI:
```python
try:
    from services.sync_service import SyncService
    SyncService().volcar_local_a_sheets(modulo="laboral", forzar=True)
    logger.info("[deploy] Sincronización post-deploy ejecutada exitosamente.")
except Exception as e_sync:
    logger.warning(f"[deploy] Sincronización post-deploy diferida: {e_sync}")
```
