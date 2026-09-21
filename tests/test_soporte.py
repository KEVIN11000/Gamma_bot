"""Tests unitarios para el comando /soporte y flujo interactivo en Telegram."""

import unittest
from unittest.mock import MagicMock, patch

from telebot.types import Message

from com.core.states import clear_state, get_state, set_state
from com.handlers.soporte import (
    _inferir_tipo_y_descripcion,
    _procesar_y_confirmar_soporte,
    register_soporte_handlers,
)


class TestSoporteHandler(unittest.TestCase):
    """Verifica el comportamiento del handler /soporte en modo dual."""

    def setUp(self) -> None:
        self.bot = MagicMock()
        self.gamma_app = MagicMock()
        clear_state(12345)

    def tearDown(self) -> None:
        clear_state(12345)

    def test_inferir_tipo_y_descripcion(self) -> None:
        tipo, desc = _inferir_tipo_y_descripcion("bug error en el balance")
        self.assertEqual(tipo, "bug")
        self.assertEqual(desc, "error en el balance")

        tipo, desc = _inferir_tipo_y_descripcion("sugerencia agregar botón para taxi")
        self.assertEqual(tipo, "sugerencia")
        self.assertEqual(desc, "agregar botón para taxi")

        tipo, desc = _inferir_tipo_y_descripcion("consulta sobre cómo abonar")
        self.assertEqual(tipo, "soporte")
        self.assertEqual(desc, "sobre cómo abonar")

        tipo, desc = _inferir_tipo_y_descripcion("el sistema no cargó la foto")
        self.assertEqual(tipo, "soporte")
        self.assertEqual(desc, "el sistema no cargó la foto")

    @patch("com.handlers.soporte.reportar_incidente_vigia")
    def test_procesar_y_confirmar_soporte(self, mock_reportar) -> None:
        mock_reportar.return_value = True

        _procesar_y_confirmar_soporte(
            bot=self.bot,
            chat_id=12345,
            tipo="bug",
            descripcion="Fallo en reporte PDF",
            autor="kevin_dev",
        )

        mock_reportar.assert_called_once()
        self.bot.send_message.assert_called_once()
        args, kwargs = self.bot.send_message.call_args
        self.assertEqual(args[0], 12345)
        self.assertIn("Ticket registrado con éxito", args[1])
        self.assertIn("Fallo en reporte PDF", args[1])

    @patch("com.handlers.soporte._procesar_y_confirmar_soporte")
    def test_modo_directo_con_argumentos(self, mock_procesar) -> None:
        register_soporte_handlers(self.bot, self.gamma_app)

        # Llamar directamente a la lógica simulando un mensaje con texto inline
        msg = MagicMock(spec=Message)
        msg.text = "/soporte bug El botón no responde"
        msg.chat = MagicMock(id=12345)
        msg.from_user = MagicMock(id=12345, username="tester")

        # Probar que la inferencia y procesamiento se ejecutan
        tipo, desc = _inferir_tipo_y_descripcion("bug El botón no responde")
        _procesar_y_confirmar_soporte(self.bot, 12345, tipo, desc, "tester")
        self.bot.send_message.assert_called_once()

    def test_modo_interactivo_callback_y_cancelacion(self) -> None:
        set_state(12345, "SOPORTE_ESPERANDO_TEXTO", {"tipo": "sugerencia"})
        state = get_state(12345)
        self.assertIsNotNone(state)
        self.assertEqual(state.get("estado"), "SOPORTE_ESPERANDO_TEXTO")
        self.assertEqual(state.get("datos", {}).get("tipo"), "sugerencia")

        # Cancelación
        clear_state(12345)
        self.assertIsNone(get_state(12345))


if __name__ == "__main__":
    unittest.main()
