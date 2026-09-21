from __future__ import annotations

from typing import Any

from logic.constants import (
    ENCABEZADOS_LIBRO_DIARIO,
    ENCABEZADOS_CIERRES_HISTORICOS,
    ENCABEZADOS_OBLIGACIONES_MAESTRO,
    ENCABEZADOS_PRESUPUESTO_BASE,
)

# Simple repository that delegates to existing logic classes.
# In a full refactor we would replace direct calls to AgenteFinanciero, etc.


class SheetsRepository:
    def __init__(self) -> None:
        # Lazy imports to avoid circular dependencies
        pass

        # These agents require the spreadsheet ID; we'll retrieve it from env when needed.
        self._financiero: Any | None = None
        self._autonomo: Any | None = None
        self._asistencia: Any | None = None

    def _init_agents(self, spreadsheet_id: str) -> None:
        from logic.financiero import AgenteFinanciero
        from logic.logic import AgenteAsistenciaMaterias, AgenteAutonomoHoras

        self._financiero = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        self._autonomo = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
        self._asistencia = AgenteAsistenciaMaterias()

    # Example method used by handlers (add more as needed)
    def add_gasto(self, data: dict) -> None:
        if self._financiero is None:
            raise RuntimeError("Repository not initialized with spreadsheet ID")
        # Assume AgenteFinanciero has a method `agregar_gasto` (placeholder)
        if hasattr(self._financiero, "agregar_gasto"):
            self._financiero.agregar_gasto(data)
        else:
            raise NotImplementedError("AgenteFinanciero.agregar_gasto not implemented")

    def _ensure_headers(self, ws, sheet_name: str) -> None:
        headers_map = {
            "Obligaciones_Maestro": ENCABEZADOS_OBLIGACIONES_MAESTRO,
            "Libro_Diario": ENCABEZADOS_LIBRO_DIARIO,
            "Cierres_Historicos": ENCABEZADOS_CIERRES_HISTORICOS,
            "Presupuesto_Base": ENCABEZADOS_PRESUPUESTO_BASE,
        }
        if sheet_name in headers_map:
            try:
                first_row = ws.row_values(1)
            except Exception:
                first_row = []
            if not first_row:
                ws.append_row(headers_map[sheet_name])

    def _get_sheet(self, sheet_name: str):
        if not hasattr(self, "_wb"):
            from logic.logic import ConexionSheets
            import os

            cliente = ConexionSheets.obtener_cliente()
            if cliente is None:
                raise RuntimeError("No se pudo obtener cliente de Google Sheets")
            spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID", os.getenv("SPREADSHEET_ID"))
            if not spreadsheet_id:
                raise RuntimeError("SPREADSHEET_ID no configurado")
            self._wb = cliente.open_by_key(spreadsheet_id)

        try:
            ws = self._wb.worksheet(sheet_name)
        except Exception:
            ws = self._wb.add_worksheet(title=sheet_name, rows=100, cols=20)

        self._ensure_headers(ws, sheet_name)
        return ws

    def _get_records(self, ws: Any, expected_headers: list[str]) -> list[dict]:
        """Safely retrieves all records from worksheet.

        Tries strict validation against expected_headers first.
        If the remote sheet lacks some columns, falls back to dynamic parsing
        with expected_headers=[] to avoid breaking execution.
        """
        try:
            return ws.get_all_records(expected_headers=expected_headers)
        except Exception:
            return ws.get_all_records(expected_headers=[])

    # --- Obligaciones_Maestro ---
    def insert_obligacion(self, obligacion_dict: dict) -> None:
        ws = self._get_sheet("Obligaciones_Maestro")
        headers = ENCABEZADOS_OBLIGACIONES_MAESTRO
        row = [obligacion_dict.get(h, "") for h in headers]
        ws.append_row(row)

    def update_obligacion_estado(self, id_obligacion: str, estado: str) -> None:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = self._get_records(ws, ENCABEZADOS_OBLIGACIONES_MAESTRO)
        for idx, r in enumerate(records, start=2):  # +1 for header, +1 for 0-index
            if str(r.get("ID_Obligacion", "")) == str(id_obligacion):
                keys_lower = [k.lower() for k in r.keys()]
                estado_idx = (
                    keys_lower.index("estado") + 1 if "estado" in keys_lower else -1
                )
                if estado_idx > 0:
                    ws.update_cell(idx, estado_idx, estado)
                break

    def get_obligacion_by_id(self, id_obligacion: str) -> dict:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = self._get_records(ws, ENCABEZADOS_OBLIGACIONES_MAESTRO)
        for r in records:
            if str(r.get("ID_Obligacion", "")) == str(id_obligacion):
                return r
        return {}

    def get_obligaciones_activas(self) -> list[dict]:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = self._get_records(ws, ENCABEZADOS_OBLIGACIONES_MAESTRO)
        return [r for r in records if str(r.get("Estado", "")).lower() == "activo"]

    def update_obligacion_saldo(
        self,
        id_obligacion: str,
        nuevo_saldo: int,
        cuotas_restantes: int | None = None,
        nuevo_estado: str | None = None,
    ) -> None:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = self._get_records(ws, ENCABEZADOS_OBLIGACIONES_MAESTRO)
        for idx, r in enumerate(records, start=2):
            if str(r.get("ID_Obligacion", "")) == str(id_obligacion):
                keys_lower = [k.lower() for k in r.keys()]
                if "saldo_actual" in keys_lower:
                    saldo_idx = keys_lower.index("saldo_actual") + 1
                    ws.update_cell(idx, saldo_idx, nuevo_saldo)

                if cuotas_restantes is not None and "cuotas_restantes" in keys_lower:
                    cuotas_idx = keys_lower.index("cuotas_restantes") + 1
                    ws.update_cell(idx, cuotas_idx, cuotas_restantes)

                if nuevo_estado is not None and "estado" in keys_lower:
                    estado_idx = keys_lower.index("estado") + 1
                    ws.update_cell(idx, estado_idx, nuevo_estado)
                break

    def update_obligacion_prioridad(
        self, id_obligacion: str, orden_prioridad: int
    ) -> None:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = self._get_records(ws, ENCABEZADOS_OBLIGACIONES_MAESTRO)
        for idx, r in enumerate(records, start=2):
            if str(r.get("ID_Obligacion", "")) == str(id_obligacion):
                keys_lower = [k.lower() for k in r.keys()]
                if "orden_prioridad" in keys_lower:
                    prio_idx = keys_lower.index("orden_prioridad") + 1
                    ws.update_cell(idx, prio_idx, orden_prioridad)
                break

    def get_todas_obligaciones(self) -> list[dict]:
        ws = self._get_sheet("Obligaciones_Maestro")
        return self._get_records(ws, ENCABEZADOS_OBLIGACIONES_MAESTRO)

    # --- Libro_Diario ---
    def insert_movimiento_diario(self, movimiento_dict: dict) -> None:
        ws = self._get_sheet("Libro_Diario")
        headers = ENCABEZADOS_LIBRO_DIARIO
        row = [movimiento_dict.get(h, "") for h in headers]
        ws.append_row(row)

    def get_movimientos_mes(self, month: str, year: str) -> list[dict]:
        ws = self._get_sheet("Libro_Diario")
        records = self._get_records(ws, ENCABEZADOS_LIBRO_DIARIO)
        target_mes = f"{str(month).zfill(2)}/{year}"
        result = []
        for r in records:
            mes_str = str(r.get("Mes", ""))
            fecha_str = str(r.get("Fecha", ""))
            # Match on Mes column (format "MM/YYYY") or fallback to Fecha containing the month/year
            if mes_str == target_mes:
                result.append(r)
            elif f"/{str(month).zfill(2)}/{year}" in fecha_str:
                result.append(r)
        return result

    def get_all_movimientos(self) -> list[dict]:
        ws = self._get_sheet("Libro_Diario")
        return self._get_records(ws, ENCABEZADOS_LIBRO_DIARIO)

    # --- Cierres_Historicos ---
    def get_last_cierre_mensual(self) -> dict:
        ws = self._get_sheet("Cierres_Historicos")
        records = self._get_records(ws, ENCABEZADOS_CIERRES_HISTORICOS)
        if records:
            return records[-1]
        return {}

    def insert_cierre_mensual(self, cierre_dict: dict) -> None:
        ws = self._get_sheet("Cierres_Historicos")
        headers = ENCABEZADOS_CIERRES_HISTORICOS
        row = [cierre_dict.get(h, "") for h in headers]
        ws.append_row(row)

    # --- Presupuesto_Base ---
    def get_presupuesto_base(self) -> dict:
        ws = self._get_sheet("Presupuesto_Base")
        records = self._get_records(ws, ENCABEZADOS_PRESUPUESTO_BASE)
        if records:
            return records[0]
        return {}

    def obtener_presupuesto_base_completo(self) -> tuple[int, int]:
        from logic.logic import safe_int

        ws = self._get_sheet("Presupuesto_Base")
        records = self._get_records(ws, ENCABEZADOS_PRESUPUESTO_BASE)
        total_ingreso = 0
        total_costos = 0
        for r in records:
            tipo_flujo = (
                str(r.get("Tipo_Flujo", r.get("Tipo_Ingreso_Gasto", "")))
                .lower()
                .strip()
            )
            monto = safe_int(r.get("Monto_Mensual_Gs", 0))
            if "ingreso" in tipo_flujo:
                total_ingreso += monto
            elif "egreso" in tipo_flujo or "gasto" in tipo_flujo:
                total_costos += monto
        return total_ingreso, total_costos
