import os
from pathlib import Path
from reportlab.pdfgen import canvas
import pytest

from logic.pdf_service import DatosReporte, PDFService


class PageCounterCanvas(canvas.Canvas):
    """Canvas auxiliar para certificar el total de páginas generadas en memoria."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_paginas = 0

    def showPage(self):
        self.total_paginas += 1
        super().showPage()


def test_pdf_reporte_31_dias_una_sola_hoja_a4(tmp_path):
    """
    INVARIANTE INV-A4: Certifica empíricamente que un reporte de asistencia
    con 31 días de registros corridos y cuadro resumen de facturación con IVA
    compila estrictamente en una sola página (A4).
    """
    encabezados = [
        "Día",
        "Fecha",
        "Hora entrada",
        "Salgo almuerzo",
        "Vuelta almuerzo",
        "Hora salida",
        "Horas",
    ]
    dias_nombre = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]

    filas = []
    for i in range(1, 32):
        dia_txt = dias_nombre[(i - 1) % 7]
        fecha_txt = f"{i:02d}/10/2026"
        if (i - 1) % 7 in (4, 5, 6):  # Días de descanso / sin horas
            filas.append([dia_txt, fecha_txt, "", "", "", "", ""])
        else:
            filas.append(
                [dia_txt, fecha_txt, "08:30", "12:00", "13:00", "17:00", "7.50"]
            )

    lineas_resumen = [
        ["Horas del mes", "107,3"],
        ["Monto por hora", "$14.634"],
        ["Total Monto por Horas", "$1.569.984"],
        ["IVA 10%", "$156.998"],
        ["TOTAL IVA INCLUIDO", "$1.726.983"],
        ["IVA NO FACTURADO SEPTIEMBRE", "$177.364"],
        ["TOTAL FACTURA", "$1.904.347"],
    ]

    datos = DatosReporte(
        titulo="REGISTRO DE HORAS DEL MES DE OCTUBRE 2026 - KEVIN PERALTA",
        subtitulo="Liquidación de Servicios Profesionales • Kevin Peralta",
        encabezados=encabezados,
        filas=filas,
        lineas_resumen=lineas_resumen,
        nombre_archivo="test_reporte_31_dias.pdf",
    )

    ruta_pdf, msg = PDFService.generar_reporte_generico(datos)
    try:
        assert ruta_pdf is not None
        assert Path(ruta_pdf).exists()
        assert "Reporte generado" in msg

        # Verificación del conteo de páginas en el PDF generado
        # Usamos ReportLab pdfreader / canvas inspect
        from reportlab.pdfgen import canvas
        import pypdf

        reader = pypdf.PdfReader(ruta_pdf)
        num_paginas = len(reader.pages)
        assert (
            num_paginas == 1
        ), f"El reporte excedió a {num_paginas} páginas. Debe ser exactamente 1 hoja A4."
    except ImportError:
        # Si pypdf no está disponible, inspeccionamos el archivo binario para el marcador de página
        with open(ruta_pdf, "rb") as f:
            contenido = f.read()
            count_page = (
                contenido.count(b"/Type /Page\n")
                + contenido.count(b"/Type /Page ")
                + contenido.count(b"/Type/Page")
            )
            assert (
                count_page == 1
            ), f"El reporte generó {count_page} páginas en el binario."
    finally:
        if ruta_pdf and Path(ruta_pdf).exists():
            os.remove(ruta_pdf)
