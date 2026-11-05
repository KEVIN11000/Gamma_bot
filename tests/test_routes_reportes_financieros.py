import os
import sys
from unittest.mock import patch, MagicMock
import pytest

os.environ["TOKEN"] = "test_token_123"
os.environ["CHAT_ID"] = "123456"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"
os.environ["FLASK_ENV"] = "development"
os.environ["CRON_SECRET"] = "test_cron_secret"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["X_API_KEY"] = "test-secret-key"

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402

from logic.pdf_service import DatosReporte  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


HEADERS = {"X-API-KEY": "test-secret-key"}


def _mock_datos_financieros():
    return DatosReporte(
        titulo="LIBRO DIARIO",
        subtitulo="Mes: Noviembre",
        encabezados=["Fecha", "Tipo", "Detalle", "Factura", "Monto", "Categoría"],
        filas=[
            [
                "01/11/2026",
                "Gasto",
                "Supermercado Stock",
                "001-001-1234",
                "150.000",
                "Alimentación",
            ],
            [
                "02/11/2026",
                "Ingreso",
                "Honorarios",
                "001-002-5678",
                "4.500.000",
                "Servicios",
            ],
        ],
        lineas_resumen=[
            ["Total Ingresos:", "4.500.000 ₲"],
            ["Total Gastos:", "150.000 ₲"],
            ["Saldo Neto:", "4.350.000 ₲"],
        ],
        nombre_archivo="reporte_finanzas_test",
    )


def test_reporte_financiero_excel_unauthorized(client):
    res = client.get("/api/v1/reportes/financiero/excel")
    assert res.status_code == 401


def test_reporte_financiero_pdf_unauthorized(client):
    res = client.get("/api/v1/reportes/financiero/pdf")
    assert res.status_code == 401


@patch("logic.financiero.AgenteFinanciero.preparar_datos_reporte")
def test_reporte_excel_error_preparacion(mock_prep, client):
    mock_prep.return_value = (None, "El Libro Diario está vacío.")
    res = client.get("/api/v1/reportes/financiero/excel?mes=11", headers=HEADERS)
    assert res.status_code == 400
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "REPORTE_ERROR"


@patch("logic.financiero.AgenteFinanciero.preparar_datos_reporte")
def test_reporte_excel_success(mock_prep, client, tmp_path):
    mock_prep.return_value = (_mock_datos_financieros(), None)

    res = client.get(
        "/api/v1/reportes/financiero/excel?mes=11&anio=2026", headers=HEADERS
    )
    assert res.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in res.content_type
    )
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert "Libro_Diario_Noviembre_2026.xlsx" in res.headers.get(
        "Content-Disposition", ""
    )
    assert len(res.data) > 0


@patch("logic.financiero.AgenteFinanciero.preparar_datos_reporte")
def test_reporte_pdf_error_preparacion(mock_prep, client):
    mock_prep.return_value = (None, "No hay movimientos registrados.")
    res = client.get("/api/v1/reportes/financiero/pdf?mes=11", headers=HEADERS)
    assert res.status_code == 400
    data = res.get_json()
    assert data["code"] == "REPORTE_ERROR"


@patch("logic.pdf_service.PDFService.generar_reporte_generico")
@patch("logic.financiero.AgenteFinanciero.preparar_datos_reporte")
def test_reporte_pdf_success(mock_prep, mock_pdf, client, tmp_path):
    mock_prep.return_value = (_mock_datos_financieros(), None)
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy pdf content")
    mock_pdf.return_value = (str(dummy_pdf), "PDF generado")

    res = client.get(
        "/api/v1/reportes/financiero/pdf?mes=11&anio=2026", headers=HEADERS
    )
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert "Libro_Diario_Noviembre_2026.pdf" in res.headers.get(
        "Content-Disposition", ""
    )
    assert res.data == b"%PDF-1.4 dummy pdf content"


@patch("logic.pdf_service.PDFService.generar_reporte_generico")
@patch("logic.financiero.AgenteFinanciero.preparar_datos_reporte")
def test_reporte_pdf_generation_failure(mock_prep, mock_pdf, client):
    mock_prep.return_value = (_mock_datos_financieros(), None)
    mock_pdf.return_value = (None, "Error en motor ReportLab")

    res = client.get(
        "/api/v1/reportes/financiero/pdf?mes=11&anio=2026", headers=HEADERS
    )
    assert res.status_code == 500
    data = res.get_json()
    assert data["error"] is True
    assert data["code"] == "PDF_ERROR"
