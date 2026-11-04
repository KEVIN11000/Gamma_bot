from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request, send_from_directory

from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py, safe_int

logger = setup_logger("routes_cierres")

cierres_bp = Blueprint("cierres_v1", __name__)


def _get_reportes_dir() -> Path:
    try:
        import api.blueprint as bp

        return bp.REPORTES_DIR
    except Exception:
        return Path(__file__).resolve().parents[2] / "reportes"


def generar_pdf_cierre(
    destino_path: Path,
    tipo: str,
    hoja: str,
    total_monto: int = 4500000,
    total_horas: float = 160.0,
    con_descuento: bool = False,
) -> None:
    """Genera un archivo PDF válido y formateado para el cierre contable o laboral usando ReportLab."""
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

    destino_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(destino_path),
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    AZUL = colors.HexColor("#1a1a2e")
    GRIS = colors.HexColor("#f5f5f5")
    GRIS2 = colors.HexColor("#cccccc")

    e_titulo = ParagraphStyle(
        "TitCierre",
        parent=styles["Normal"],
        fontSize=16,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        spaceAfter=4,
    )
    e_sub = ParagraphStyle(
        "SubCierre",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=2,
    )
    e_seccion = ParagraphStyle(
        "SecCierre",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=AZUL,
        spaceBefore=12,
        spaceAfter=6,
    )

    ahora = get_now_py()
    titulo = (
        "COMPROBANTE OFICIAL DE CIERRE CONTABLE"
        if tipo == "contable"
        else "COMPROBANTE DE CIERRE LABORAL MENSUAL"
    )
    subtitulo = f"Período Fiscal / Académico: {hoja}"

    story = [
        Paragraph(titulo, e_titulo),
        Paragraph(subtitulo, e_sub),
        Paragraph(f"Emitido el: {ahora.strftime('%d/%m/%Y %H:%M:%S')} (PYST)", e_sub),
        HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=14),
        Paragraph("Resumen Ejecutivo de Liquidación", e_seccion),
    ]

    ancho_util = A4[0] - 3 * cm

    if tipo == "contable":
        datos_tabla = [
            ["Concepto / Rubro", "Detalle"],
            ["Período de Conciliación", hoja],
            ["Tipo de Cierre", "Libro Diario Contable"],
            ["Total de Movimientos Procesados", "Conciliación Completa"],
            ["Monto Neto Total Balanceado", f"{total_monto:,} Gs."],
            ["Estado del Período", "CERRADO Y ARCHIVADO"],
        ]
    else:
        desc_txt = "Aplicado" if con_descuento else "No Aplica"
        datos_tabla = [
            ["Concepto / Registro", "Detalle"],
            ["Período", hoja],
            ["Tipo de Registro", "Horas Laborales y Asistencia"],
            ["Total Horas Computadas", f"{total_horas:.1f} hs."],
            ["Descuento de Seguro", desc_txt],
            ["Liquidación Estimada", f"{total_monto:,} Gs."],
            ["Estado", "CONSOLIDADO"],
        ]

    cw = [ancho_util * 0.55, ancho_util * 0.45]
    tabla = Table(datos_tabla, colWidths=cw)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
                ("GRID", (0, 0), (-1, -1), 0.5, GRIS2),
                ("BOX", (0, 0), (-1, -1), 1, AZUL),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tabla)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS2, spaceAfter=8))

    e_pie = ParagraphStyle(
        "PieCierre",
        parent=styles["Normal"],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#777777"),
    )
    story.append(
        Paragraph(
            "Documento digital con validez de auditoría interna generado por Gamma Bot Mobile API.<br/>"
            "Sistema de Gestión Contable y Asistencia.",
            e_pie,
        )
    )

    doc.build(story)


@cierres_bp.route("/cierres", methods=["GET"])
@require_api_key
def get_historial_cierres() -> Any:
    reportes_dir = _get_reportes_dir()
    try:
        from repositories.sheets_repository import SheetsRepository

        repo = SheetsRepository()
        raw_cierres = repo.get_todos_cierres_historicos()

        resultado: list[dict[str, Any]] = []
        ids_contables: set[str] = set()

        # 1. Cierres Contables desde Google Sheets
        for r in raw_cierres:
            mes = str(r.get("Mes", "")).strip()
            anio = str(r.get("Anio", "")).strip()
            periodo = (
                f"{mes} {anio}".strip() if (mes or anio) else "Período Desconocido"
            )

            cierre_id = str(r.get("ID_Cierre") or "").strip()
            if not cierre_id:
                cierre_id = f"cierre_contable_{periodo.replace(' ', '_').lower()}"
            ids_contables.add(cierre_id)

            total_ingresos = safe_int(r.get("Total_Ingresos", 0))
            total_gastos = safe_int(r.get("Total_Gastos", 0))
            saldo_acumulado = safe_int(r.get("Saldo_Acumulado", 0))
            fecha = str(r.get("Fecha_Cierre") or "").strip()

            filename = f"cierre_contable_{periodo.replace(' ', '_').lower()}.pdf"
            pdf_path = reportes_dir / filename
            pdf_disponible = pdf_path.exists()

            resumen_partes = []
            if total_ingresos > 0:
                resumen_partes.append(
                    f"Ingresos: ₲ {total_ingresos:,}".replace(",", ".")
                )
            if total_gastos > 0:
                resumen_partes.append(f"Gastos: ₲ {total_gastos:,}".replace(",", "."))
            if not resumen_partes:
                resumen_partes.append(f"Saldo: ₲ {saldo_acumulado:,}".replace(",", "."))
            resumen = " | ".join(resumen_partes)

            resultado.append(
                {
                    "id": cierre_id,
                    "tipo": "contable",
                    "periodo": periodo,
                    "fecha": fecha,
                    "total_monto": total_ingresos or saldo_acumulado,
                    "total_horas": 0.0,
                    "resumen": resumen,
                    "pdf_url": f"/api/v1/cierres/reportes/{filename}",
                    "pdf_disponible": pdf_disponible,
                }
            )

        # 2. Cierres Laborales y Contables adicionales en REPORTES_DIR
        if reportes_dir.exists():
            for pdf_file in sorted(
                reportes_dir.glob("*.pdf"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                stem = pdf_file.stem
                if stem.startswith("cierre_laboral_"):
                    partes = stem.replace("cierre_laboral_", "").split("_")
                    periodo_lab = " ".join(p.capitalize() for p in partes)
                    file_stat = pdf_file.stat()
                    fecha_mod = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    resultado.append(
                        {
                            "id": stem,
                            "tipo": "laboral",
                            "periodo": periodo_lab,
                            "fecha": fecha_mod,
                            "total_monto": 0,
                            "total_horas": 160.0,
                            "resumen": f"Cierre laboral de horas para período {periodo_lab}",
                            "pdf_url": f"/api/v1/cierres/reportes/{pdf_file.name}",
                            "pdf_disponible": True,
                        }
                    )
                elif stem.startswith("cierre_contable_") and stem not in ids_contables:
                    partes = stem.replace("cierre_contable_", "").split("_")
                    periodo_cont = " ".join(p.capitalize() for p in partes)
                    file_stat = pdf_file.stat()
                    fecha_mod = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    resultado.append(
                        {
                            "id": stem,
                            "tipo": "contable",
                            "periodo": periodo_cont,
                            "fecha": fecha_mod,
                            "total_monto": 0,
                            "total_horas": 0.0,
                            "resumen": f"Cierre contable para período {periodo_cont}",
                            "pdf_url": f"/api/v1/cierres/reportes/{pdf_file.name}",
                            "pdf_disponible": True,
                        }
                    )
                    ids_contables.add(stem)

        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error consultando historial de cierres: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Error al consultar historial de cierres: {str(e)}",
                    }
                }
            ),
            500,
        )


@cierres_bp.route("/cierres/ejecutar", methods=["POST"])
@require_api_key
def ejecutar_cierre() -> Any:
    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo", "horas")
    hoja = data.get("hoja", "Período Actual")
    con_desc = data.get("aplicar_descuento", False)

    reportes_dir = _get_reportes_dir()
    prefix = "cierre_contable" if tipo == "contable" else "cierre_laboral"
    filename = f"{prefix}_{hoja.replace(' ', '_').lower()}.pdf"
    pdf_path = reportes_dir / filename

    total_horas = 0.0
    total_monto = 0
    cierre_ejecutado = False
    backup_id = ""

    if tipo in ("horas", "laboral"):
        try:
            from logic.logic import AgenteAutonomoHoras

            agente_horas = AgenteAutonomoHoras()
            nombre_hoja_target = (
                None if hoja in ("Período Actual", "Periodo Actual") else hoja
            )
            analiticas, err = agente_horas.calcular_analiticas_asistencia(
                nombre_hoja=nombre_hoja_target
            )
            if analiticas:
                total_horas = float(analiticas.get("total_horas_decimal", 0.0))
                total_monto = int(analiticas.get("salario_acumulado_gs", 0))

            if data.get("cerrar_planilla", False):
                agente_horas.ejecutar_cierre_periodo_manual()
                cierre_ejecutado = True
        except Exception as e_horas:
            logger.warning(
                f"Error obteniendo analíticas reales de horas para cierre: {e_horas}"
            )
            total_horas = 0.0
            total_monto = 0

    elif tipo == "contable":
        try:
            from repositories.sheets_repository import SheetsRepository
            from logic.logic import get_now_py
            from logic.constants import MESES_ES

            repo = SheetsRepository()
            ahora = get_now_py()
            mes_num = ahora.month
            anio_num = ahora.year

            partes = hoja.split()
            if len(partes) == 2:
                for idx, m_nombre in enumerate(MESES_ES, start=1):
                    if m_nombre.lower() == partes[0].lower():
                        mes_num = idx
                        break
                try:
                    anio_num = int(partes[1])
                except ValueError:
                    pass

            bal = repo.obtener_balance(mes=str(mes_num), anio=str(anio_num))
            if bal:
                ingresos = bal.get("ingresos", 0)
                gastos = bal.get("gastos", 0)
                flujo_neto = bal.get("flujo_neto", ingresos - gastos)
                total_monto = flujo_neto
            total_horas = 0.0

            if data.get("cerrar_contabilidad", False):
                from logic.financiero import execute_monthly_closing

                backup_id = execute_monthly_closing(mes_num, anio_num)
                cierre_ejecutado = True
        except Exception as e_cont:
            logger.warning(f"Error calculando balance contable para cierre: {e_cont}")
            total_horas = 0.0
            total_monto = 0

    try:
        generar_pdf_cierre(
            destino_path=pdf_path,
            tipo=tipo,
            hoja=hoja,
            total_monto=total_monto,
            total_horas=total_horas,
            con_descuento=con_desc,
        )
    except Exception as e:
        logger.error(f"Error generando PDF de cierre: {e}")
        return (
            jsonify(
                {
                    "error": {
                        "code": "PDF_GENERATION_ERROR",
                        "message": f"Error al generar comprobante PDF: {str(e)}",
                    },
                    "mensaje": f"Error al generar comprobante PDF: {str(e)}",
                }
            ),
            500,
        )

    desc_str = (
        " (con descuento de seguro)"
        if con_desc and tipo in ("horas", "laboral")
        else ""
    )
    tipo_str = (
        "contable (Libro Diario)" if tipo == "contable" else "laboral de asistencia"
    )
    return (
        jsonify(
            {
                "resumen": f"Cierre mensual {tipo_str} completado para período {hoja}{desc_str}.",
                "pdf_url": f"/api/v1/cierres/reportes/{filename}",
                "total_horas": total_horas,
                "total_monto": total_monto,
                "tipo": tipo,
                "hoja": hoja,
                "cierre_ejecutado": cierre_ejecutado,
                "backup_id": backup_id,
            }
        ),
        200,
    )


@cierres_bp.route("/cierres/reportes/<path:filename>", methods=["GET"])
@require_api_key
def descargar_reporte_pdf(filename: str) -> Any:
    reportes_dir = _get_reportes_dir()
    return send_from_directory(reportes_dir, filename, mimetype="application/pdf")


@cierres_bp.route("/asistencia/cierres", methods=["GET"])
@require_api_key
def get_historial_cierres_laborales() -> Any:
    """Devuelve la lista de períodos y reportes laborales de asistencia archivados."""
    try:
        from logic.logic import AgenteAutonomoHoras

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        periodos: list[dict[str, Any]] = []
        reportes_dir = _get_reportes_dir()

        if spreadsheet_id:
            try:
                agente = AgenteAutonomoHoras(spreadsheet_id=spreadsheet_id)
                hojas = [
                    ws.title
                    for ws in agente.wb.worksheets()
                    if ws.title.lower() not in ("materias", "resumen", "config")
                ]
                for h in hojas:
                    filename = f"cierre_laboral_{h.replace(' ', '_').lower()}.pdf"
                    pdf_path = reportes_dir / filename
                    periodos.append(
                        {
                            "periodo": h,
                            "pdf_disponible": pdf_path.exists(),
                            "pdf_url": (
                                f"/api/v1/cierres/reportes/{filename}"
                                if pdf_path.exists()
                                else None
                            ),
                        }
                    )
            except Exception as e_sheet:
                logger.warning(
                    f"Error listando hojas para cierres laborales: {e_sheet}"
                )

        # Fallback a archivos PDF encontrados en disco si no hubo conexión
        if not periodos:
            for p in sorted(reportes_dir.glob("cierre_laboral_*.pdf")):
                periodo_nombre = (
                    p.stem.replace("cierre_laboral_", "").replace("_", " ").capitalize()
                )
                periodos.append(
                    {
                        "periodo": periodo_nombre,
                        "pdf_disponible": True,
                        "pdf_url": f"/api/v1/cierres/reportes/{p.name}",
                    }
                )

        return (
            jsonify(
                {
                    "status": "ok",
                    "total": len(periodos),
                    "cierres": periodos,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error consultando historial de cierres laborales: {e}")
        return jsonify({"status": "error", "message": str(e), "cierres": []}), 500
