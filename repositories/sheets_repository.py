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

    # Flujo A / Deudas_Maestro
    def insert_deuda(self, deuda_dict: dict) -> None:
        ws = self._get_sheet("Deudas_Maestro")
        ws.append_row(list(deuda_dict.values()))

    # Flujo B / Deudas_Maestro
    def get_deudas_activas(self) -> list[dict]:
        ws = self._get_sheet("Deudas_Maestro")
        records = ws.get_all_records()
        return [r for r in records if str(r.get("estado", "")).lower() == "activa"]

    # Flujo C / Pagos_Abonos_Detalle
    def insert_pago_abono(self, pago_dict: dict) -> None:
        ws = self._get_sheet("Pagos_Abonos_Detalle")
        ws.append_row(list(pago_dict.values()))

    # Libro_Diario
    def insert_movimiento_diario(self, movimiento_dict: dict) -> None:
        ws = self._get_sheet("Libro_Diario")
        ws.append_row(list(movimiento_dict.values()))

    def get_movimientos_mes(self, month: int, year: int) -> list[dict]:
        ws = self._get_sheet("Libro_Diario")
        records = ws.get_all_records()
        return [r for r in records if str(r.get("mes", "")) == str(month) and str(r.get("year", "")) == str(year)]

    def get_all_movimientos(self) -> list[dict]:
        ws = self._get_sheet("Libro_Diario")
        return ws.get_all_records()

    # Flujo D / Cierres_Mensuales
    def insert_cierre_mensual(self, cierre_dict: dict) -> None:
        ws = self._get_sheet("Cierres_Mensuales")
        ws.append_row(list(cierre_dict.values()))

    # Presupuesto_Base
    def get_presupuesto_base(self) -> dict:
        ws = self._get_sheet("Presupuesto_Base")
        records = ws.get_all_records()
        if records:
            return records[0]
        return {}

    # Flujo E / Simulador_Proyectos
    def insert_simulacion(self, simulacion_dict: dict) -> None:
        ws = self._get_sheet("Simulador_Proyectos")
        ws.append_row(list(simulacion_dict.values()))

    # Flujo F / Simulador_Proyectos
    def update_simulacion_estado(self, project_id: str, estado: str) -> None:
        ws = self._get_sheet("Simulador_Proyectos")
        records = ws.get_all_records()
        for idx, r in enumerate(records, start=2): # +1 for header, +1 for 0-index
            if str(r.get("id_proyecto", "")) == str(project_id):
                ws.update_cell(idx, list(r.keys()).index("estado") + 1, estado)
                break
