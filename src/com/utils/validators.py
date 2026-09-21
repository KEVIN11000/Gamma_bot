from __future__ import annotations

import datetime
import re
from typing import Any, Sequence


def parse_monto(val: Any) -> int:
    """Parsea y valida un monto monetario a entero positivo.

    Elimina puntos, comas, espacios y símbolos comunes ('Gs.', '$').

    Raises:
        ValueError: Si el valor no representa un monto numérico positivo.
    """
    if val is None:
        raise ValueError("El monto no puede ser nulo.")

    if isinstance(val, (int, float)):
        monto_int = int(val)
        if monto_int <= 0:
            raise ValueError("El monto debe ser un número entero positivo.")
        return monto_int

    val_str = str(val).strip()
    # Eliminar prefijos/sufijos de moneda comunes y separadores
    val_clean = re.sub(r"(?i)\b(gs|guaranies|pyg|\$)\b", "", val_str)
    val_clean = val_clean.replace(".", "").replace(",", "").replace(" ", "").strip()

    if not val_clean.isdigit():
        raise ValueError("El monto debe ser numérico.")

    monto = int(val_clean)
    if monto <= 0:
        raise ValueError("El monto debe ser un número entero positivo.")

    return monto


def parse_cuotas(val: Any) -> int:
    """Parsea y valida el número de cuotas de una obligación.

    Raises:
        ValueError: Si las cuotas no corresponden a un entero mayor a 0.
    """
    if val is None:
        raise ValueError("El número de cuotas no puede ser nulo.")

    try:
        cuotas = int(str(val).strip())
    except (ValueError, TypeError):
        raise ValueError("El número de cuotas debe ser un número entero.")

    if cuotas <= 0:
        raise ValueError("El número de cuotas debe ser mayor a 0.")

    return cuotas


def validate_fecha(fecha_str: str) -> str:
    """Valida que una cadena de texto tenga el formato de fecha DD/MM/YYYY.

    Raises:
        ValueError: Si el formato es incorrecto o la fecha es inválida.
    """
    if not fecha_str or not isinstance(fecha_str, str):
        raise ValueError(
            "La fecha debe ser una cadena no vacía con formato DD/MM/YYYY."
        )

    fecha_limpia = fecha_str.strip()
    try:
        dt = datetime.datetime.strptime(fecha_limpia, "%d/%m/%Y")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        raise ValueError(
            f"Formato de fecha inválido '{fecha_str}'. Debe ser DD/MM/YYYY."
        )


def validate_categoria(cat: str, valid_categories: Sequence[str]) -> str:
    """Valida que una categoría pertenezca a la lista de categorías permitidas.

    Realiza una búsqueda insensible a mayúsculas y minúsculas.

    Raises:
        ValueError: Si la categoría no coincide con ninguna permitida.
    """
    if not cat or not isinstance(cat, str):
        raise ValueError("La categoría no puede estar vacía.")

    cat_norm = cat.strip().lower()
    for valid in valid_categories:
        if valid.strip().lower() == cat_norm:
            return valid

    valid_str = ", ".join(valid_categories)
    raise ValueError(f"Categoría '{cat}' inválida. Opciones válidas: {valid_str}")
