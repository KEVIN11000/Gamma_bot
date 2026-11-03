from __future__ import annotations

from src.utils.nlp_parser import FinanceNLParser, ParsedMovementResult


class TestFinanceNLParser:
    """Suite de pruebas unitarias exhaustivas para FinanceNLParser."""

    def test_parse_gasto_standard_thousands(self):
        """Verifica parsing de gasto con separador de miles y comercio conocido."""
        res = FinanceNLParser.parse("Gasto 45.000 almuerzo en Don Vito")
        assert isinstance(res, ParsedMovementResult)
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 45000.0
        assert res.categoria == "Comida"
        assert res.proveedor_cliente == "Don Vito"
        assert res.confianza >= 0.70

    def test_parse_gasto_suffix_k(self):
        """Verifica parsing con sufijo 'k' y comercio en minúscula."""
        res = FinanceNLParser.parse("gasté 15k en biggie pan y leche")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 15000.0
        assert res.categoria == "Supermercado"
        assert res.proveedor_cliente == "Biggie"

    def test_parse_gasto_suffix_mil(self):
        """Verifica parsing con 'mil'."""
        res = FinanceNLParser.parse("pagué 20 mil en farmacia")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 20000.0
        assert res.categoria == "Salud"

    def test_parse_ingreso_suffix_m(self):
        """Verifica parsing de ingreso con notación 'M'."""
        res = FinanceNLParser.parse("ingreso 2M sueldo")
        assert res.valido is True
        assert res.tipo_movimiento == "Ingreso"
        assert res.monto == 2000000.0
        assert res.categoria == "Sueldo"

    def test_parse_ingreso_millones(self):
        """Verifica parsing de cobro en millones con cliente."""
        res = FinanceNLParser.parse("cobré 1.5 millones honorarios de cliente Juan")
        assert res.valido is True
        assert res.tipo_movimiento == "Ingreso"
        assert res.monto == 1500000.0
        assert res.categoria == "Sueldo"

    def test_parse_combustible_known_merchant(self):
        """Verifica extracción de combustible con estación Petrobras."""
        res = FinanceNLParser.parse("Pague 120.000 combustible en Petrobras")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 120000.0
        assert res.categoria == "Combustible"
        assert res.proveedor_cliente == "Petrobras"

    def test_parse_plain_amount_currency(self):
        """Verifica número plano con indicación de moneda Gs."""
        res = FinanceNLParser.parse("Compre cafe 25000 Gs en Juan Valdez")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 25000.0
        assert res.categoria == "Comida"
        assert "Juan Valdez" in res.proveedor_cliente

    def test_parse_supermercado_superseis(self):
        """Verifica categorización y comercio Superseis."""
        res = FinanceNLParser.parse("Compra de 85000 en Superseis")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 85000.0
        assert res.categoria == "Supermercado"
        assert res.proveedor_cliente == "Superseis"

    def test_parse_transporte_uber(self):
        """Verifica viaje en Uber."""
        res = FinanceNLParser.parse("Uber 35000 al trabajo")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 35000.0
        assert res.categoria == "Transporte"
        assert res.proveedor_cliente == "Uber"

    def test_parse_servicios_ande(self):
        """Verifica pago de servicio público ANDE."""
        res = FinanceNLParser.parse("Pague luz ande 350.000")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 350000.0
        assert res.categoria == "Servicios"
        assert res.proveedor_cliente == "ANDE"

    def test_parse_salud_punto_farma(self):
        """Verifica remedios en Punto Farma."""
        res = FinanceNLParser.parse("remedios en Punto Farma 45000")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 45000.0
        assert res.categoria == "Salud"
        assert res.proveedor_cliente == "Punto Farma"

    def test_parse_empty_string(self):
        """Verifica que string vacío retorne valido=False."""
        res = FinanceNLParser.parse("")
        assert res.valido is False
        assert res.monto == 0.0
        assert res.confianza == 0.0

    def test_parse_none(self):
        """Verifica que None retorne valido=False."""
        res = FinanceNLParser.parse(None)
        assert res.valido is False
        assert res.monto == 0.0
        assert res.confianza == 0.0

    def test_parse_no_numbers(self):
        """Verifica que texto sin números retorne valido=False."""
        res = FinanceNLParser.parse("Hola buenas tardes como estas")
        assert res.valido is False
        assert res.monto == 0.0
        assert res.confianza == 0.0

    def test_parse_amount_with_decimals_usd(self):
        """Verifica extracción con decimales y moneda USD."""
        res = FinanceNLParser.parse("Gasto 15.50 usd en libro")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 15.5

    def test_parse_implicit_gasto(self):
        """Verifica que una compra sin prefijo explícito 'gasto' asuma Gasto."""
        res = FinanceNLParser.parse("pizza 60000")
        assert res.valido is True
        assert res.tipo_movimiento == "Gasto"
        assert res.monto == 60000.0
        assert res.categoria == "Comida"

    def test_to_dict_method(self):
        """Verifica serialización del resultado a diccionario."""
        res = FinanceNLParser.parse("Gasto 50000 combustible en Shell")
        d = res.to_dict()
        assert isinstance(d, dict)
        assert d["valido"] is True
        assert d["tipo_movimiento"] == "Gasto"
        assert d["monto"] == 50000.0
        assert d["categoria"] == "Combustible"
        assert d["proveedor_cliente"] == "Shell"
        assert "descripcion" in d
        assert "confianza" in d
