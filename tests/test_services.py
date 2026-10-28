import os
from pathlib import Path
import unittest
from logic.pdf_service import DatosReporte, PDFService
from services.calendar_service import CalendarService
from services.drive_service import DriveService


class TestServices(unittest.TestCase):
    def test_calendar_create_event(self):
        result = CalendarService.create_event("Test", "2026-09-04", "Desc")
        self.assertEqual(result, "")

    def test_calendar_mark_completed(self):
        result = CalendarService.mark_event_completed("mock_id")
        self.assertFalse(result)

    def test_drive_upload_backup(self):
        result = DriveService.upload_backup("/path/to/file.csv")
        self.assertEqual(result, "")

    def test_drive_upload_backup_fallback_local(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("Fecha,Concepto,Total\n01/10/2026,Prueba,1000\n")
            temp_path = f.name
        try:
            with unittest.mock.patch.object(
                DriveService, "_get_drive_client", return_value=None
            ):
                result = DriveService.upload_backup(temp_path)
                self.assertTrue(result.startswith("local:"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_drive_upload_backup_mock_drive_success(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("Fecha,Concepto,Total\n01/10/2026,Prueba,1000\n")
            temp_path = f.name
        try:
            mock_client = unittest.mock.MagicMock()
            mock_files = mock_client.files.return_value
            mock_create = mock_files.create.return_value
            mock_create.execute.return_value = {"id": "mock_drive_id_999"}

            with unittest.mock.patch.object(
                DriveService, "_get_drive_client", return_value=mock_client
            ):
                result = DriveService.upload_backup(temp_path)
                self.assertEqual(result, "mock_drive_id_999")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_pdf_service_generar_reporte_horas(self):
        """Valida que PDFService compile correctamente con la tabla de resumen estandarizada."""
        datos = DatosReporte(
            titulo="REGISTRO DE HORAS DEL MES DE OCTUBRE 2026 - KEVIN PERALTA",
            subtitulo="Octubre 2026",
            encabezados=[
                "Día",
                "Fecha",
                "Hora entrada",
                "Salgo almuerzo",
                "Vuelta almuerzo",
                "Hora salida",
                "Horas",
            ],
            filas=[
                [
                    "Martes",
                    "29/09/2026",
                    "09:10",
                    "12:47",
                    "13:16",
                    "17:05",
                    "7.43",
                ],
                [
                    "Jueves",
                    "01/10/2026",
                    "08:30",
                    "12:19",
                    "12:59",
                    "17:05",
                    "7.92",
                ],
            ],
            lineas_resumen=[
                ["mes", "15.4"],
                ["hora", "$14,634"],
                ["por Horas", "$225,364"],
                ["IVA 10%", "$22,536"],
                ["INCLUIDO", "$247,900"],
                ["SALDO ANTERIOR", "$177,364"],
                ["FACTURA", "$425,264"],
            ],
            nombre_archivo="test_reporte_horas.pdf",
        )

        ruta_pdf, msg = PDFService.generar_reporte_generico(datos)
        self.assertIsNotNone(ruta_pdf)
        self.assertTrue(Path(ruta_pdf).exists())
        self.assertIn("Reporte generado", msg)

        # Limpieza
        if ruta_pdf and Path(ruta_pdf).exists():
            os.remove(ruta_pdf)


if __name__ == "__main__":
    unittest.main()
