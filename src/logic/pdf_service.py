from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional  # noqa: F401

from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("pdf_service")

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
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                HRFlowable,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

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
                leftMargin=1.0 * cm,
                rightMargin=1.0 * cm,
                topMargin=1.0 * cm,
                bottomMargin=1.0 * cm,
            )

            AZUL = colors.HexColor("#1a1a2e")
            GRIS = colors.HexColor("#f8f9fa")
            GRIS2 = colors.HexColor("#cccccc")
            GRIS_BANNER = colors.HexColor("#e6e8ec")
            TEXTO_MUTED = colors.HexColor("#555555")

            ancho_util = A4[0] - 2.0 * cm
            story = []

            # 1. Banner superior unificado (A1:G1)
            t_banner = Table(
                [
                    [
                        Paragraph(
                            f"<b>{datos.titulo}</b>",
                            ParagraphStyle(
                                "Bann",
                                fontSize=10,
                                leading=12,
                                alignment=TA_CENTER,
                                textColor=AZUL,
                                fontName="Helvetica-Bold",
                            ),
                        )
                    ]
                ],
                colWidths=[ancho_util],
            )
            t_banner.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), GRIS_BANNER),
                        ("BOX", (0, 0), (-1, -1), 0.8, AZUL),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t_banner)
            story.append(Spacer(1, 3))

            # 2. Subtítulo y fecha de emisión en 1 fila compacta
            fecha_str = get_now_py().strftime("%d/%m/%Y %I:%M %p")
            t_sub = Table(
                [
                    [
                        Paragraph(
                            f"{datos.subtitulo}",
                            ParagraphStyle(
                                "SubL",
                                fontSize=8,
                                leading=10,
                                textColor=TEXTO_MUTED,
                                fontName="Helvetica",
                            ),
                        ),
                        Paragraph(
                            f"Emisión: {fecha_str} (America/Asuncion)",
                            ParagraphStyle(
                                "SubR",
                                fontSize=8,
                                leading=10,
                                alignment=2,
                                textColor=TEXTO_MUTED,
                                fontName="Helvetica",
                            ),
                        ),
                    ]
                ],
                colWidths=[ancho_util * 0.6, ancho_util * 0.4],
            )
            t_sub.setStyle(
                TableStyle(
                    [
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(t_sub)
            story.append(Spacer(1, 3))

            # 3. Tabla de registros principales (31 días calibrados)
            es_asistencia_larga = len(datos.filas) >= 20
            padding_v = 2.2 if es_asistencia_larga else 4.0
            font_size_datos = 7.5 if es_asistencia_larga else 8.0

            if datos.encabezados:
                col_w = [ancho_util / len(datos.encabezados)] * len(datos.encabezados)
                tabla_filas = [datos.encabezados]
                for f in datos.filas:
                    f_completa = (f + [""] * len(datos.encabezados))[
                        : len(datos.encabezados)
                    ]
                    tabla_filas.append(f_completa)

                tabla = Table(tabla_filas, colWidths=col_w, repeatRows=1)
                t_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTSIZE", (0, 1), (-1, -1), font_size_datos),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
                    ("GRID", (0, 0), (-1, -1), 0.3, GRIS2),
                    ("BOX", (0, 0), (-1, -1), 0.8, AZUL),
                    ("TOPPADDING", (0, 0), (-1, -1), padding_v),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), padding_v),
                ]
                if len(datos.encabezados) >= 7:
                    t_style.append(("ALIGN", (0, 1), (0, -1), "LEFT"))
                    t_style.append(("LEFTPADDING", (0, 1), (0, -1), 4))
                    t_style.append(("ALIGN", (-1, 1), (-1, -1), "RIGHT"))
                    t_style.append(("RIGHTPADDING", (-1, 1), (-1, -1), 4))

                tabla.setStyle(TableStyle(t_style))
                story.append(tabla)

            # 4. Cuadro Resumen Inferior
            spacer_resumen = 5 if es_asistencia_larga else 10
            story.append(Spacer(1, spacer_resumen))

            if datos.lineas_resumen:
                filas_resumen_render = []
                tiene_header = (
                    len(datos.lineas_resumen) > 0
                    and str(datos.lineas_resumen[0][0]).strip().lower() == "resumen"
                )
                if not tiene_header:
                    filas_resumen_render.append(["Resumen", "Cantidades"])
                filas_resumen_render.extend(datos.lineas_resumen)

                ancho_res = min(250.0, ancho_util * 0.5)
                cw = [ancho_res * 0.60, ancho_res * 0.40]
                pad_res = 2.5 if es_asistencia_larga else 4.0

                tabla_resumen = Table(
                    filas_resumen_render, colWidths=cw, hAlign="RIGHT"
                )
                tabla_resumen.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 8),
                            ("ALIGN", (0, 0), (0, -1), "LEFT"),
                            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                            ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 1), (-1, -2), font_size_datos),
                            ("FONTSIZE", (0, -1), (-1, -1), font_size_datos + 1.0),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, GRIS]),
                            ("BACKGROUND", (0, -1), (-1, -1), AZUL),
                            ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                            ("BOX", (0, 0), (-1, -1), 0.8, AZUL),
                            ("GRID", (0, 0), (-1, -1), 0.3, GRIS2),
                            ("TOPPADDING", (0, 0), (-1, -1), pad_res),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), pad_res),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(tabla_resumen)

            # 5. Pie de página institucional
            story.append(Spacer(1, 6))
            footer = Paragraph(
                "Documento compilado y respaldado automáticamente por <b>Gamma Bot Platform</b> • Formato Oficial de Liquidación de Horas",
                ParagraphStyle(
                    "Foot",
                    fontSize=7,
                    leading=9,
                    alignment=TA_CENTER,
                    textColor=colors.HexColor("#888888"),
                    fontName="Helvetica",
                ),
            )
            story.append(footer)

            doc.build(story)
            return ruta_pdf, f"✅ Reporte generado — {datos.subtitulo}"
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return None, f"❌ Error al generar reporte: {type(e).__name__} - {str(e)}"
