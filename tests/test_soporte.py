"""Tests unitarios para el comando /soporte y flujo interactivo en Telegram."""

import unittest
from unittest.mock import MagicMock, patch
import os

from telebot.types import Message, CallbackQuery

from com.core.states import clear_state, get_state
from com.handlers.soporte import (
    _inferir_tipo_y_descripcion,
    register_soporte_handlers,
)


class TestSoporteHandler(unittest.TestCase):
    """Verifica el comportamiento del handler /soporte en modo dual."""

    def setUp(self) -> None:
        self.bot = MagicMock()
        self.gamma_app = MagicMock()
        self.handlers = {}
        self.callback_handlers = []
        self.msg_func_handlers = []

        os.environ["CHAT_ID"] = "12345"

        def mock_message_handler(**kwargs):
            def decorator(func):
                if "commands" in kwargs:
                    for cmd in kwargs["commands"]:
                        self.handlers[cmd] = func
                elif "func" in kwargs:
                    self.msg_func_handlers.append((kwargs["func"], func))
                return func

            return decorator

        def mock_callback_handler(**kwargs):
            def decorator(func):
                if "func" in kwargs:
                    self.callback_handlers.append((kwargs["func"], func))
                return func

            return decorator

        self.bot.message_handler = mock_message_handler
        self.bot.callback_query_handler = mock_callback_handler

        register_soporte_handlers(self.bot, self.gamma_app)
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
    @patch("com.handlers.soporte._guardar_ticket_fallback")
    def test_procesar_y_confirmar_soporte(self, mock_fallback, mock_reportar) -> None:
        mock_reportar.return_value = True

        msg = MagicMock(spec=Message)
        msg.text = "/soporte bug El botón no responde"
        msg.chat = MagicMock(id=12345)
        msg.from_user = MagicMock(id=12345, username="tester")

        self.handlers["soporte"](msg)

        mock_reportar.assert_called_once()
        self.bot.send_message.assert_called_once()
        args, kwargs = self.bot.send_message.call_args
        self.assertEqual(args[0], 12345)
        self.assertIn("Ticket registrado", args[1])

    @patch("com.handlers.soporte.reportar_incidente_vigia")
    @patch("com.handlers.soporte._guardar_ticket_fallback")
    def test_modo_interactivo_callback_y_flujo_completo(
        self, mock_fallback, mock_reportar
    ) -> None:
        mock_reportar.return_value = True

        msg = MagicMock(spec=Message)
        msg.text = "/soporte"
        msg.chat = MagicMock(id=12345)
        msg.from_user = MagicMock(id=12345, username="tester")

        self.handlers["soporte"](msg)
        self.bot.send_message.assert_called_once()

        call = MagicMock(spec=CallbackQuery)
        call.id = "mocked_id"
        call.data = "soporte_tipo:sugerencia"
        call.from_user = MagicMock(id=12345)
        call.message = MagicMock(chat=MagicMock(id=12345), message_id=999)

        for condition, handler in self.callback_handlers:
            if condition(call):
                handler(call)
                break

        state = get_state(12345)
        self.assertIsNotNone(state)
        self.assertEqual(state.get("estado"), "SOPORTE_ESPERANDO_TEXTO")
        self.assertEqual(state.get("datos", {}).get("tipo"), "sugerencia")
        self.bot.edit_message_text.assert_called_once()

        text_msg = MagicMock(spec=Message)
        text_msg.text = "Mejorar los colores"
        text_msg.chat = MagicMock(id=12345)
        text_msg.from_user = MagicMock(id=12345, username="tester")

        for condition, handler in self.msg_func_handlers:
            if condition(text_msg):
                handler(text_msg)
                break

        mock_reportar.assert_called_once()
        args, kwargs = mock_reportar.call_args
        self.assertEqual(kwargs["origen"], "telegram-soporte")

        self.assertIsNone(get_state(12345))


if __name__ == "__main__":
    unittest.main()
