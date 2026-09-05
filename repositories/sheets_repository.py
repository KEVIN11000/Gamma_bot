from __future__ import annotations

from typing import Any

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

    def _get_sheet(self, sheet_name: str):
        if not hasattr(self, '_wb'):
            from logic.logic import ConexionSheets
            import os
            cliente = ConexionSheets.obtener_cliente()
            spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID", os.getenv("SPREADSHEET_ID"))
            self._wb = cliente.open_by_key(spreadsheet_id)
        
        try:
            return self._wb.worksheet(sheet_name)
        except Exception:
            return self._wb.add_worksheet(title=sheet_name, rows=100, cols=20)

    # --- Obligaciones_Maestro ---
    def insert_obligacion(self, obligacion_dict: dict) -> None:
        ws = self._get_sheet("Obligaciones_Maestro")
        headers = ["ID_Obligacion", "Tipo", "Nombre_Concepto", "Monto_Inicial", "Saldo_Actual", "Estado", "Tasa_Interes", "Fecha_Vencimiento", "Cuotas", "Event_ID"]
        row = [obligacion_dict.get(h, "") for h in headers]
        ws.append_row(row)

    def update_obligacion_estado(self, id_obligacion: str, estado: str) -> None:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = ws.get_all_records()
        for idx, r in enumerate(records, start=2): # +1 for header, +1 for 0-index
            if str(r.get("ID_Obligacion", "")) == str(id_obligacion):
                keys_lower = [k.lower() for k in r.keys()]
                estado_idx = keys_lower.index("estado") + 1 if "estado" in keys_lower else -1
                if estado_idx > 0:
                    ws.update_cell(idx, estado_idx, estado)
                break

    def get_obligacion_by_id(self, id_obligacion: str) -> dict:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = ws.get_all_records()
        for r in records:
            if str(r.get("ID_Obligacion", "")) == str(id_obligacion):
                return r
        return {}
        
    def get_obligaciones_activas(self) -> list[dict]:
        ws = self._get_sheet("Obligaciones_Maestro")
        records = ws.get_all_records()
        return [r for r in records if str(r.get("Estado", "")).lower() == "activo"]

    # --- Libro_Diario ---
    def insert_movimiento_diario(self, movimiento_dict: dict) -> None:
        ws = self._get_sheet("Libro_Diario")
        headers = ["ID_Transaccion", "Fecha", "Concepto", "Tipo_Movimiento", "Monto_Total", "Tasa_IVA", "Monto_Gravado", "Monto_IVA", "Clasificacion_IVA", "ID_Obligacion"]
        row = [movimiento_dict.get(h, "") for h in headers]
        ws.append_row(row)

    def get_movimientos_mes(self, month: str, year: str) -> list[dict]:
        ws = self._get_sheet("Libro_Diario")
        records = ws.get_all_records()
        result = []
        for r in records:
            fecha_str = str(r.get("Fecha", ""))
            if f"{year}-{str(month).zfill(2)}" in fecha_str or f"{str(month).zfill(2)}-{year}" in fecha_str:
                result.append(r)
        return result

    def get_all_movimientos(self) -> list[dict]:
        ws = self._get_sheet("Libro_Diario")
        return ws.get_all_records()

    # --- Cierres_Historicos ---
    def get_last_cierre_mensual(self) -> dict:
        ws = self._get_sheet("Cierres_Historicos")
        records = ws.get_all_records()
        if records:
            return records[-1]
        return {}

    def insert_cierre_mensual(self, cierre_dict: dict) -> None:
        ws = self._get_sheet("Cierres_Historicos")
        headers = ["Mes_Anio", "Total_Ingresos_Efectivo", "Total_Egresos_Efectivo", "IVA_Debito_Fiscal", "IVA_Credito_Fiscal", "Liquidacion_IVA", "Estado_IVA", "Margen_Libre_Disponible", "Saldo_Acumulado_Actual"]
        row = [cierre_dict.get(h, "") for h in headers]
        ws.append_row(row)

    # --- Presupuesto_Base ---
    def get_presupuesto_base(self) -> dict:
        ws = self._get_sheet("Presupuesto_Base")
        records = ws.get_all_records()
        if records:
            return records[0]
        return {}
