#!/usr/bin/env python3
"""Script de migración y realineación para la pestaña 'Obligaciones_Maestro'.

Detecta desfasajes columnares generados por la adición de la columna 'Tipo'
en el índice 2 (columna B) y realinea las filas de datos para que coincidan 1:1
con ENCABEZADOS_OBLIGACIONES_MAESTRO.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

# Agregar directorio src al path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from logic.constants import ENCABEZADOS_OBLIGACIONES_MAESTRO  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
)
logger = logging.getLogger("migracion_obligaciones")

ESTADOS_CONOCIDOS = {
    "activo",
    "pausado",
    "cancelado",
    "simulado",
    "pagado",
    "finalizado",
    "inactivo",
}
TIPOS_CONOCIDOS = {
    "deuda",
    "prestamo",
    "tarjeta",
    "gasto fijo",
    "servicio",
    "credito",
    "obligacion",
}


def realinear_fila_obligacion(
    fila: list[str], tipo_default: str = "Deuda"
) -> tuple[list[str], bool]:
    """Evalúa una fila de Obligaciones_Maestro y la realinea al esquema de 16 columnas.

    Retorna:
        tuple[list[str], bool]: (fila_resultante_16_cols, fue_modificada)
    """
    if not fila or not any(c.strip() for c in fila):
        return fila, False

    # Copia limpia
    vals = [str(c).strip() for c in fila]

    # Caso A: Fila con exactamente 15 columnas (esquema legacy sin columna 'Tipo')
    if len(vals) == 15:
        # vals[0]: ID, vals[1]: Nombre, vals[2]: Entidad, vals[3]: Monto_Inicial,
        # vals[4]: Saldo_Actual, vals[5]: Estado, vals[6]: Cuota_Referencia_Gs, etc.
        nueva_fila = [vals[0], tipo_default] + vals[1:]
        # Asegurar longitud 16
        while len(nueva_fila) < 16:
            nueva_fila.append("")
        return nueva_fila[:16], True

    # Caso B: Fila con 16 columnas pero con el desfasaje horizontal heredado
    # En el desfasaje: fila[5] tiene el Estado ("Activo") en lugar de Saldo_Actual,
    # y fila[1] tiene el Nombre en lugar de Tipo.
    if len(vals) >= 16:
        val_col1_lower = vals[1].lower() if len(vals) > 1 else ""
        val_col5_lower = vals[5].lower() if len(vals) > 5 else ""
        val_col6_lower = vals[6].lower() if len(vals) > 6 else ""

        # Si col 6 ya es un estado válido o col 1 ya es un tipo válido, está bien alineada
        if val_col6_lower in ESTADOS_CONOCIDOS or val_col1_lower in TIPOS_CONOCIDOS:
            # Asegurar longitud exacta 16
            return (vals + [""] * 16)[:16], False

        # Si col 5 contiene un estado conocido, confirma el corrimiento
        if val_col5_lower in ESTADOS_CONOCIDOS:
            # Reorganizar: vals[0]=ID, Tipo=tipo_default, vals[1]=Nombre, vals[2]=Entidad,
            # vals[3]=Monto_Inicial, vals[4]=Saldo_Actual, vals[5]=Estado, vals[6..]=Cuota...
            nueva_fila = [
                vals[0],
                tipo_default,
                vals[1],
                vals[2],
                vals[3],
                vals[4],
                vals[5],
            ] + vals[6:15]
            while len(nueva_fila) < 16:
                nueva_fila.append("")
            return nueva_fila[:16], True

        # Si la fila tiene más de 16 columnas, truncar
        if len(vals) > 16:
            return vals[:16], True

        return vals[:16], False

    # Caso C: Fila corta (< 15 columnas)
    pad = (vals + [""] * 16)[:16]
    return pad, (len(vals) != 16)


def migrar_hoja_obligaciones_maestro(
    ws: Any = None, dry_run: bool = True
) -> dict[str, Any]:
    """Ejecuta la migración sobre la pestaña 'Obligaciones_Maestro' de Google Sheets."""
    if ws is None:
        from logic.logic import ConexionSheets

        cliente = ConexionSheets.obtener_cliente()
        if not cliente:
            raise RuntimeError("No se pudo conectar con Google Sheets")
        spreadsheet_id = os.getenv("LIBRO_CONTABLE_ID", os.getenv("SPREADSHEET_ID"))
        if not spreadsheet_id:
            raise RuntimeError("SPREADSHEET_ID no configurado")
        wb = cliente.open_by_key(spreadsheet_id)
        ws = wb.worksheet("Obligaciones_Maestro")

    filas = ws.get_all_values()
    if not filas:
        logger.info("La pestaña 'Obligaciones_Maestro' está vacía.")
        return {"filas_procesadas": 0, "filas_migradas": 0}

    encabezado_esperado = ENCABEZADOS_OBLIGACIONES_MAESTRO

    filas_datos = filas[1:]
    filas_migradas: list[tuple[int, list[str], list[str]]] = []
    filas_finales: list[list[str]] = [encabezado_esperado]

    for idx, fila in enumerate(filas_datos, start=2):
        fila_alineada, modificada = realinear_fila_obligacion(fila)
        filas_finales.append(fila_alineada)
        if modificada:
            filas_migradas.append((idx, fila, fila_alineada))

    logger.info(
        f"Diagnóstico: Total filas = {len(filas)}, "
        f"Filas de datos que requieren realineación = {len(filas_migradas)}"
    )

    for idx, origen, destino in filas_migradas:
        logger.info(f"Fila {idx} desfasada:")
        logger.info(f"  Antes : {origen[:7]}")
        logger.info(f"  Después: {destino[:7]}")

    if dry_run:
        logger.info("🔍 MODO DRY-RUN: No se realizaron cambios en Google Sheets.")
        return {
            "filas_procesadas": len(filas_datos),
            "filas_migradas": len(filas_migradas),
            "dry_run": True,
        }

    # Aplicar cambios en batch
    logger.info("🚀 APLICANDO CAMBIOS en Google Sheets...")
    ws.update(f"A1:P{len(filas_finales)}", filas_finales)

    # Invalidar caché en sheets_repository si está cargado
    try:
        from repositories.sheets_repository import _sheets_cache

        _sheets_cache.clear()
    except Exception as e_cache:
        logger.warning(f"No se pudo limpiar caché: {e_cache}")

    logger.info("✅ Migración completada exitosamente.")
    return {
        "filas_procesadas": len(filas_datos),
        "filas_migradas": len(filas_migradas),
        "dry_run": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrar y realinear Obligaciones_Maestro en Google Sheets"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica los cambios en Google Sheets (por defecto solo ejecuta --dry-run)",
    )
    args = parser.parse_args()

    migrar_hoja_obligaciones_maestro(dry_run=not args.apply)


if __name__ == "__main__":
    main()
