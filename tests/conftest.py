import os
import pytest
from unittest.mock import MagicMock

# Set environment variables for tests
os.environ["SPREADSHEET_ID"] = "dummy_spreadsheet_id"
os.environ["CALENDAR_ID"] = "dummy_calendar_id"
os.environ["LIBRO_CONTABLE_ID"] = "dummy_libro_contable_id"
os.environ["MONTO_POR_HORA"] = "30000"

@pytest.fixture(autouse=True)
def mock_google_services(monkeypatch):
    from logic.logic import ConexionSheets
    
    mock_cliente = MagicMock()
    mock_cliente.open_by_key.return_value = MagicMock()
    monkeypatch.setattr(ConexionSheets, "obtener_cliente", lambda: mock_cliente)
    
    mock_servicio = MagicMock()
    monkeypatch.setattr(ConexionSheets, "obtener_servicio_calendar", lambda: mock_servicio)
