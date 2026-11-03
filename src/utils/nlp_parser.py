from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ParsedMovementResult:
    valido: bool
    tipo_movimiento: str
    monto: float
    categoria: str
    proveedor_cliente: str
    descripcion: str
    confianza: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valido": self.valido,
            "tipo_movimiento": self.tipo_movimiento,
            "monto": self.monto,
            "categoria": self.categoria,
            "proveedor_cliente": self.proveedor_cliente,
            "descripcion": self.descripcion,
            "confianza": self.confianza,
        }


class FinanceNLParser:
    """Parser determinista de lenguaje natural para transacciones financieras en español."""

    # Categorías y palabras clave asociadas
    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "Comida": [
            "almuerzo",
            "cena",
            "desayuno",
            "merienda",
            "comida",
            "restaurante",
            "bar",
            "cafe",
            "café",
            "pizza",
            "lomito",
            "empanada",
            "hamburguesa",
            "asado",
            "don vito",
            "mcdonald",
            "burger",
        ],
        "Combustible": [
            "combustible",
            "nafta",
            "diesel",
            "gasolina",
            "petrobras",
            "shell",
            "copetrol",
            "barcos",
            "enex",
            "puma",
        ],
        "Supermercado": [
            "super",
            "supermercado",
            "biggie",
            "superseis",
            "stock",
            "arete",
            "despensa",
            "almacen",
            "viveres",
            "leche",
            "pan",
            "mercaderia",
        ],
        "Transporte": [
            "pasaje",
            "uber",
            "bolt",
            "taxi",
            "colectivo",
            "peaje",
            "estacionamiento",
            "remis",
        ],
        "Salud": [
            "farmacia",
            "medicamento",
            "remedio",
            "doctor",
            "consulta",
            "punto farma",
            "catedral",
            "farmatotal",
            "odontologo",
            "dentista",
        ],
        "Servicios": [
            "luz",
            "ande",
            "agua",
            "essap",
            "internet",
            "tigo",
            "personal",
            "claro",
            "alquiler",
            "expensas",
            "netflix",
            "spotify",
        ],
        "Sueldo": [
            "sueldo",
            "salario",
            "honorarios",
            "adelanto",
            "comision",
            "quincena",
            "aguinaldo",
            "cobro cliente",
            "factura cobrada",
        ],
        "Ocio": [
            "cine",
            "juego",
            "boliche",
            "cerveza",
            "fiesta",
            "concierto",
            "teatro",
            "viaje",
            "hotel",
        ],
    }

    # Comercios conocidos para extracción directa de entidad
    KNOWN_MERCHANTS: list[str] = [
        "Petrobras",
        "Shell",
        "Copetrol",
        "Puma",
        "Enex",
        "Biggie",
        "Superseis",
        "Stock",
        "Don Vito",
        "Punto Farma",
        "Farmacia Catedral",
        "Farmatotal",
        "Uber",
        "Bolt",
        "McDonalds",
        "Burger King",
        "ANDE",
        "ESSAP",
        "Tigo",
        "Personal",
        "Claro",
    ]

    KEYWORDS_GASTO = {
        "gasto",
        "gaste",
        "gasté",
        "compre",
        "compré",
        "compra",
        "pague",
        "pagué",
        "pago",
        "salida",
        "consumo",
    }

    KEYWORDS_INGRESO = {
        "ingreso",
        "ingresó",
        "cobre",
        "cobré",
        "cobro",
        "recibi",
        "recibí",
        "gane",
        "gané",
        "entrada",
        "sueldo",
        "salario",
        "honorarios",
        "adelanto",
        "deposito",
        "depósito",
        "quincena",
    }

    @classmethod
    def parse(cls, text: str | None) -> ParsedMovementResult:
        """Parsea una cadena de texto libre y extrae los datos de un movimiento financiero.

        Args:
            text: Frase enviada por el usuario (ej: "Gasto 45.000 almuerzo en Don Vito").

        Returns:
            Instancia de ParsedMovementResult con los datos normalizados.
        """
        if not text or not text.strip():
            return ParsedMovementResult(
                valido=False,
                tipo_movimiento="Gasto",
                monto=0.0,
                categoria="Varios",
                proveedor_cliente="S/N",
                descripcion="",
                confianza=0.0,
            )

        clean_text = text.strip()
        lower_text = clean_text.lower()

        # 1. Extracción del monto
        monto, confidence_amount = cls._extraer_monto(clean_text)
        if monto <= 0:
            return ParsedMovementResult(
                valido=False,
                tipo_movimiento="Gasto",
                monto=0.0,
                categoria="Varios",
                proveedor_cliente="S/N",
                descripcion=clean_text,
                confianza=0.0,
            )

        # 2. Detección del tipo de movimiento (Gasto vs Ingreso)
        tipo_movimiento, confidence_type = cls._determinar_tipo(lower_text)

        # 3. Detección de la categoría
        categoria, confidence_category = cls._determinar_categoria(lower_text)

        # 4. Extracción del comercio / proveedor / cliente
        proveedor_cliente, confidence_merchant = cls._extraer_comercio(clean_text)

        # 5. Generación de descripción limpia
        descripcion = cls._generar_descripcion(
            clean_text, tipo_movimiento, categoria, proveedor_cliente
        )

        # 6. Cálculo de confianza global
        confianza = min(
            1.0,
            round(
                confidence_amount * 0.45
                + confidence_type * 0.25
                + confidence_category * 0.15
                + confidence_merchant * 0.15,
                2,
            ),
        )

        valido = confianza >= 0.60 and monto > 0

        return ParsedMovementResult(
            valido=valido,
            tipo_movimiento=tipo_movimiento,
            monto=monto,
            categoria=categoria,
            proveedor_cliente=proveedor_cliente,
            descripcion=descripcion,
            confianza=confianza,
        )

    @classmethod
    def _extraer_monto(cls, text: str) -> tuple[float, float]:
        """Extrae el monto monetario del texto y su nivel de confianza."""
        # Patrón 1: Notación en 'k' / 'K' / 'mil' (ej: 15k, 45.5k, 20 mil)
        match_k = re.search(
            r"(?i)\b(\d+(?:[.,]\d+)?)\s*(?:k|mil)\b",
            text,
        )
        if match_k:
            raw_num = match_k.group(1).replace(",", ".")
            try:
                val = float(raw_num) * 1000.0
                return val, 1.0
            except ValueError:
                pass

        # Patrón 2: Notación en 'M' / 'm' / 'millon' / 'millones' (ej: 2.5M, 1M, 2 millones)
        match_m = re.search(
            r"(?i)\b(\d+(?:[.,]\d+)?)\s*(?:m|millon|millón|millones)\b",
            text,
        )
        if match_m:
            raw_num = match_m.group(1).replace(",", ".")
            try:
                val = float(raw_num) * 1000000.0
                return val, 1.0
            except ValueError:
                pass

        # Patrón 3: Moneda explícita previa o posterior (ej: 45.000 Gs, Gs. 50000, $15.50, USD 100)
        match_curr = re.search(
            r"(?i)(?:(gs\.?|pyg|\$|usd|guaran[ií]es)\s*(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?))|"
            r"(?:(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*(gs\.?|pyg|\$|usd|guaran[ií]es))",
            text,
        )
        if match_curr:
            val_str = (match_curr.group(2) or match_curr.group(3) or "").strip()
            if val_str:
                if "." in val_str and len(val_str.split(".")[-1]) == 3:
                    val_clean = val_str.replace(".", "")
                else:
                    val_clean = val_str.replace(",", ".")
                try:
                    v = float(val_clean)
                    if v > 0:
                        return v, 0.90
                except ValueError:
                    pass

        # Buscar todos los candidatos numéricos en el texto
        # 3a. Números con separador de miles paraguayo/latino: 45.000, 1.500.000
        match_thousands = re.findall(r"\b(\d{1,3}(?:\.\d{3})+(?:,\d+)?)\b", text)
        if match_thousands:
            # Tomar el candidato con mayor probabilidad (evitando fechas cortas)
            cand = match_thousands[0]
            cand_clean = cand.replace(".", "").replace(",", ".")
            try:
                return float(cand_clean), 0.95
            except ValueError:
                pass

        # 3b. Números planos (ej: 50000, 120000)
        candidatos = re.findall(r"\b\d{3,10}\b", text)
        if candidatos:
            # Si hay números >= 1000, usualmente representan el monto
            try:
                nums = [float(c) for c in candidatos]
                # Elegir el mayor si hay varios, o el primero que parezca monto
                return max(nums), 0.85
            except ValueError:
                pass

        # 3c. Cualquier número suelto >= 1
        loose_match = re.search(r"\b\d+(?:[.,]\d+)?\b", text)
        if loose_match:
            cand = loose_match.group(0).replace(",", ".")
            try:
                val = float(cand)
                conf = 0.35 if val < 100 else 0.65
                return val, conf
            except ValueError:
                pass

        return 0.0, 0.0

    @classmethod
    def _determinar_tipo(cls, lower_text: str) -> tuple[str, float]:
        """Determina si la transacción es Gasto o Ingreso."""
        words = set(re.findall(r"\b\w+\b", lower_text))

        has_ingreso = bool(words & cls.KEYWORDS_INGRESO)
        has_gasto = bool(words & cls.KEYWORDS_GASTO)

        if has_ingreso and not has_gasto:
            return "Ingreso", 1.0
        if has_gasto and not has_ingreso:
            return "Gasto", 1.0

        # Contexto secundario: si contiene palabras como 'sueldo', 'cobro', 'honorarios' -> Ingreso
        if any(
            w in lower_text
            for w in ["sueldo", "salario", "cobro", "honorarios", "cliente"]
        ):
            return "Ingreso", 0.90

        # Por defecto en transacciones cotidianas se asume Gasto con baja certeza si no hay verbos
        return "Gasto", 0.30

    @classmethod
    def _determinar_categoria(cls, lower_text: str) -> tuple[str, float]:
        """Asigna la categoría canónica basada en palabras clave."""
        for cat, kw_list in cls.CATEGORY_KEYWORDS.items():
            for kw in kw_list:
                if re.search(rf"\b{re.escape(kw)}\b", lower_text):
                    return cat, 0.95

        return "Varios", 0.50

    @classmethod
    def _extraer_comercio(cls, text: str) -> tuple[str, float]:
        """Extrae el comercio, cliente o proveedor involucrado."""
        lower_text = text.lower()

        # 1. Búsqueda en comercios conocidos
        for merchant in cls.KNOWN_MERCHANTS:
            if re.search(rf"(?i)\b{re.escape(merchant.lower())}\b", lower_text):
                return merchant, 1.0

        # 2. Extracción mediante preposiciones: "en <Comercio>" o "de <Cliente/Comercio>"
        # Ej: "en Don Vito", "en Super Los Jardines", "de Juan Perez"
        match_prep = re.search(
            r"(?i)\b(?:en|de|a)\s+([A-ZÁÉÍÓÚa-záéíóú0-9\s]{2,30}?)(?=(?:\s+(?:de|por|\d|gs|mil|k|\.))|$)",
            text,
        )
        if match_prep:
            candidate = match_prep.group(1).strip()
            # Filtrar si el candidato es una categoría conocida o palabra genérica
            if candidate.lower() not in {
                "un",
                "una",
                "el",
                "la",
                "los",
                "las",
                "mi",
                "mis",
            }:
                words = candidate.split()
                if len(words) <= 4:
                    return candidate.title(), 0.85

        return "S/N", 0.40

    @classmethod
    def _generar_descripcion(
        cls,
        raw_text: str,
        tipo: str,
        categoria: str,
        proveedor: str,
    ) -> str:
        """Construye una descripción legible para el movimiento."""
        # Limpiar texto de prefijos de acción explícitos
        cleaned = re.sub(
            r"(?i)\b(gasto|gasté|compre|compré|pague|pagué|ingreso|cobre|cobré|recibí|recibi)\b",
            "",
            raw_text,
        ).strip()

        # Limpiar montos obvios de la descripción
        cleaned = re.sub(
            r"(?i)\b\d+(?:[.,]\d+)?\s*(?:k|m|mil|millones|gs\.?|pyg|\$|usd)?\b",
            "",
            cleaned,
        ).strip()

        # Limpiar signos residuales
        cleaned = re.sub(r"\s+", " ", cleaned).strip("-:,; ")

        if cleaned and len(cleaned) >= 3:
            return cleaned.capitalize()

        if proveedor != "S/N":
            return f"{categoria} en {proveedor}"

        return f"{tipo} - {categoria}"
