from __future__ import annotations

from typing import Any

# Simple repository that delegates to existing logic classes.
# In a full refactor we would replace direct calls to AgenteFinanciero, etc.

class SheetsRepository:
    def __init__(self) -> None:
        # Lazy imports to avoid circular dependencies
        from logic.financiero import AgenteFinanciero
        from logic.logic import AgenteAutonomoHoras, AgenteAsistenciaMaterias
        # These agents require the spreadsheet ID; we'll retrieve it from env when needed.
        self._financiero: Any | None = None
        self._autonomo: Any | None = None
        self._asistencia: Any | None = None

    def _init_agents(self, spreadsheet_id: str) -> None:
        from logic.financiero import AgenteFinanciero
        from logic.logic import AgenteAutonomoHoras, AgenteAsistenciaMaterias
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

    # Add other CRUD wrappers as required by the bot handlers.
