from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytz

from logger_config import setup_logger

logger = setup_logger("pdf_service")

tz_py = pytz.timezone("America/Buenos_Aires")
BASE_DIR = Path(__file__).resolve().parents[1]


@dataclass
class DatosReporte:
    """
    Class DatosReporte.
    """
    titulo: str
    subtitulo: str
    encabezados: list
    filas: list
    lineas_resumen: list  # Lista de listas: [["Concepto", "Monto"], ...]
    nombre_archivo: str


class PDFService:
    """
    Class PDFService.
    """
    
    @staticmethod
    def generar_reporte_generico(datos: DatosReporte):
        """
        generar_reporte_generico method/function.
        
        Args:
            datos: Description for datos.
        
        Returns:
            Description of the return value.
        
        Raises:
            Exception: Description of the exception.
        """
        try:
            import re
            import uuid

            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import (ParagraphStyle,
                                              getSampleStyleSheet)
            from reportlab.lib.units import cm
            from reportlab.platypus import (HRFlowable, Paragraph,
                                            SimpleDocTemplate, Spacer, Table,
                                            TableStyle)

            directorio = os.path.join(BASE_DIR, "reportes")
            os.makedirs(directorio, exist_ok=True)

            # Sanitizar nombre (prevenir Path Traversal en Windows)
            nombre_sano = re.sub(r"[^\w\-\.]", "_", datos.nombre_archivo)

            # Evitar colisión/Race Condition
            sufijo_random = uuid.uuid4().hex[:8]
            base, ext = os.path.splitext(nombre_sano)
            nombre_final = f"{base}_{sufijo_random}{ext}"

            ruta_pdf = os.path.join(directorio, nombre_final)

            doc = SimpleDocTemplate(
                ruta_pdf,
                pagesize=A4,
                leftMargin=1.5 * cm,
                rightMargin=1.5 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
            )
            estilos = getSampleStyleSheet()

            def estilo(nombre, **kw):
                """
                estilo method/function.
                
                Args:
                    nombre: Description for nombre.
                    **kw: Arbitrary keyword arguments.
                
                Returns:
                    Description of the return value.
                
                Raises:
                    Exception: Description of the exception.
                """
                return ParagraphStyle(nombre, parent=estilos["Normal"], **kw)

            e_titulo = estilo(
                "Tit",
                fontSize=16,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
                spaceAfter=3,
            )
            e_sub = estilo(
                "Sub",
                fontSize=10,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#555555"),
                spaceAfter=2,
            )
            e_seccion = estilo(
                "Sec",
                fontSize=11,
                fontName="Helvetica-Bold",
                spaceBefore=14,
                spaceAfter=6,
                textColor=colors.HexColor("#1a1a2e"),
            )

            AZUL = colors.HexColor("#1a1a2e")
            GRIS = colors.HexColor("#f5f5f5")
            GRIS2 = colors.HexColor("#cccccc")

            story = []
            story.append(Paragraph(datos.titulo, e_titulo))
            story.append(Paragraph(datos.subtitulo, e_sub))
            story.append(
                Paragraph(
                    f"Generado: {datetime.now(tz_py).strftime('%d/%m/%Y  %I:%M %p')}",
                    e_sub,
                )
            )
            story.append(
                HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=14)
            )

            story.append(Paragraph("Registros del período", e_seccion))
            ancho_util = A4[0] - 3 * cm

            if datos.encabezados:
                col_w = [ancho_util / len(datos.encabezados)] * len(datos.encabezados)
                tabla_filas = [datos.encabezados]
                for f in datos.filas:
                    f_completa = (f + [""] * len(datos.encabezados))[
                        : len(datos.encabezados)
                    ]
                    tabla_filas.append(f_completa)

                tabla = Table(tabla_filas, colWidths=col_w, repeatRows=1)
                tabla.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 8),
                            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                            ("FONTSIZE", (0, 1), (-1, -1), 8),
                            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
                            ("GRID", (0, 0), (-1, -1), 0.4, GRIS2),
                            ("BOX", (0, 0), (-1, -1), 1, AZUL),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.append(tabla)

            story.append(Spacer(1, 20))
            story.append(
                HRFlowable(width="100%", thickness=0.5, color=GRIS2, spaceAfter=6)
            )
            story.append(Paragraph("Resumen del período", e_seccion))

            if datos.lineas_resumen:
                cw = [ancho_util * 0.6, ancho_util * 0.4]
                tabla_resumen = Table(datos.lineas_resumen, colWidths=cw)
                tabla_resumen.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -2), 10),
                            ("FONTSIZE", (0, -1), (-1, -1), 12),
                            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                            ("ROWBACKGROUNDS", (0, 0), (-1, -2), [colors.white, GRIS]),
                            ("BACKGROUND", (0, -1), (-1, -1), AZUL),
                            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                            ("BOX", (0, 0), (-1, -1), 1, AZUL),
                            ("LINEABOVE", (0, -1), (-1, -1), 1.5, AZUL),
                            ("TOPPADDING", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ]
                    )
                )
                story.append(tabla_resumen)

            doc.build(story)
            return ruta_pdf, f"✅ Reporte generado — {datos.subtitulo}"
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return None, f"❌ Error al generar reporte: {type(e).__name__} - {str(e)}"
