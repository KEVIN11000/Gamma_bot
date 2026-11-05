from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any
from flask import Blueprint, jsonify, request, send_file

from api.security import require_api_key
from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("routes_reportes")

reportes_bp = Blueprint("reportes_v1", __name__)

MESES_ANIO = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def _get_reportes_dir() -> Path:
    try:
        import api.blueprint as bp

        return bp.REPORTES_DIR
    except Exception:
        return Path(__file__).resolve().parents[2] / "reportes"


def _resolver_mes_y_anio() -> tuple[str, str]:
    ahora = get_now_py()
    mes_arg = request.args.get("mes", "").strip()
    anio_arg = request.args.get("anio", "").strip() or str(ahora.year)

    if mes_arg.isdigit():
        idx = int(mes_arg)
        nombre_mes = (
            MESES_ANIO[idx - 1] if 1 <= idx <= 12 else MESES_ANIO[ahora.month - 1]
        )
    elif mes_arg and mes_arg.title() in MESES_ANIO:
        nombre_mes = mes_arg.title()
    elif not mes_arg:
        nombre_mes = MESES_ANIO[ahora.month - 1]
    else:
        nombre_mes = mes_arg.title()

    return nombre_mes, anio_arg


def _generar_excel_financiero(datos: Any, output_dir: Path) -> str:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    output_dir.mkdir(parents=True, exist_ok=True)
    nombre_archivo = f"Libro_Diario_{uuid.uuid4().hex[:8]}.xlsx"
    ruta = output_dir / nombre_archivo

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Libro Diario"

    font_titulo = Font(name="Calibri", size=14, bold=True, color="1F497D")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fill_header = PatternFill(
        start_color="1F497D", end_color="1F497D", fill_type="solid"
    )
    font_bold = Font(name="Calibri", size=11, bold=True)
    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    thin = Side(border_style="thin", color="D9D9D9")
    border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Título principal
    ws.merge_cells("A1:F1")
    cell_tit = ws["A1"]
    tit = getattr(datos, "titulo", "LIBRO DIARIO")
    sub = getattr(datos, "subtitulo", "")
    cell_tit.value = f"{tit} — {sub}".strip(" —")
    cell_tit.font = font_titulo
    cell_tit.alignment = align_center
    ws.row_dimensions[1].height = 25

    # Encabezados de columnas
    encabezados = getattr(
        datos,
        "encabezados",
        ["Fecha", "Tipo", "Detalle", "Factura", "Monto", "Categoría"],
    )
    for col_idx, h in enumerate(encabezados, start=1):
        c = ws.cell(row=3, column=col_idx, value=str(h))
        c.font = font_header
        c.fill = fill_header
        c.alignment = align_center
        c.border = border_cell
    ws.row_dimensions[3].height = 20

    # Filas de transacciones
    filas = getattr(datos, "filas", [])
    row_num = 4
    for fila in filas:
        for col_idx, val in enumerate(fila, start=1):
            c = ws.cell(row=row_num, column=col_idx, value=val)
            c.border = border_cell
            if col_idx == 5:
                c.alignment = align_right
            else:
                c.alignment = Alignment(vertical="center")
        row_num += 1

    # Líneas de resumen (Totales, Posición IVA)
    lineas_resumen = getattr(datos, "lineas_resumen", [])
    if lineas_resumen:
        row_num += 1
        for linea in lineas_resumen:
            if len(linea) >= 2:
                c_lbl = ws.cell(row=row_num, column=4, value=str(linea[0]))
                c_lbl.font = font_bold
                c_lbl.alignment = align_right
                c_val = ws.cell(row=row_num, column=5, value=str(linea[1]))
                c_val.font = font_bold
                c_val.alignment = align_right
                row_num += 1

    # Auto-ajuste de ancho de columnas
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(ruta)
    return str(ruta)


@reportes_bp.route("/reportes/financiero/excel", methods=["GET"])
@require_api_key
def descargar_reporte_financiero_excel() -> Any:
    """Genera y descarga la planilla nativa Excel (.xlsx) con los movimientos del Libro Diario."""
    try:
        nombre_mes, anio = _resolver_mes_y_anio()

        from logic.financiero import AgenteFinanciero

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        datos, error = agente.preparar_datos_reporte(mes=nombre_mes)

        if error:
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "REPORTE_ERROR",
                        "mensaje": str(error),
                    }
                ),
                400,
            )

        output_dir = _get_reportes_dir()
        ruta_archivo = _generar_excel_financiero(datos, output_dir=output_dir)

        nombre_descarga = f"Libro_Diario_{nombre_mes}_{anio}.xlsx"
        return send_file(
            ruta_archivo,
            mimetype=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            as_attachment=True,
            download_name=nombre_descarga,
        )
    except Exception as exc:
        logger.error(f"Error generando reporte Excel financiero: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "INTERNAL_ERROR",
                    "mensaje": f"No se pudo generar el reporte Excel: {exc}",
                }
            ),
            500,
        )


@reportes_bp.route("/reportes/financiero/pdf", methods=["GET"])
@require_api_key
def descargar_reporte_financiero_pdf() -> Any:
    """Genera y descarga el reporte PDF oficial con el balance y movimientos del Libro Diario."""
    try:
        nombre_mes, anio = _resolver_mes_y_anio()

        from logic.financiero import AgenteFinanciero
        from logic.pdf_service import PDFService

        spreadsheet_id = (
            os.getenv("LIBRO_CONTABLE_ID") or os.getenv("SPREADSHEET_ID") or ""
        )
        agente = AgenteFinanciero(spreadsheet_id=spreadsheet_id)
        datos, error = agente.preparar_datos_reporte(mes=nombre_mes)

        if error:
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "REPORTE_ERROR",
                        "mensaje": str(error),
                    }
                ),
                400,
            )

        ruta_pdf, msg_pdf = PDFService.generar_reporte_generico(datos)
        if not ruta_pdf or not os.path.exists(ruta_pdf):
            return (
                jsonify(
                    {
                        "error": True,
                        "code": "PDF_ERROR",
                        "mensaje": f"Fallo al compilar archivo PDF: {msg_pdf}",
                    }
                ),
                500,
            )

        nombre_descarga = f"Libro_Diario_{nombre_mes}_{anio}.pdf"
        return send_file(
            ruta_pdf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nombre_descarga,
        )
    except Exception as exc:
        logger.error(f"Error generando reporte PDF financiero: {exc}", exc_info=True)
        return (
            jsonify(
                {
                    "error": True,
                    "code": "INTERNAL_ERROR",
                    "mensaje": f"No se pudo generar el reporte PDF: {exc}",
                }
            ),
            500,
        )
