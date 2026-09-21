import unittest
from unittest.mock import MagicMock, patch

# Mock the decorators BEFORE importing the handlers

patch("com.core.security.auth_required", lambda bot: lambda f: f).start()
patch("com.core.errors.safe_handler", lambda bot, logger: lambda f: f).start()

from com.handlers.deudas import register_deudas_handlers
import com.core.states as states


class TestDeudasHandlers(unittest.TestCase):
    def setUp(self):
        self.bot_mock = MagicMock()
        self.gamma_app_mock = MagicMock()

        self.handlers = {}

        def mock_message_handler(**kwargs):
            def decorator(func):
                if "commands" in kwargs:
                    for cmd in kwargs["commands"]:
                        self.handlers[cmd] = func
                return func

            return decorator

        self.bot_mock.message_handler = mock_message_handler

        register_deudas_handlers(self.bot_mock, self.gamma_app_mock)

        states._states.clear()

    def test_handle_nueva_deuda(self):
        msg = MagicMock()
        msg.text = "/nueva_deuda"
        msg.from_user.id = 12345
        self.handlers["nueva_deuda"](msg)
        self.assertEqual(states.get_state(12345)["estado"], "NUEVA_DEUDA_P1")
        self.bot_mock.reply_to.assert_called_once()

    @patch("com.handlers.deudas.get_active_debts")
    def test_handle_deudas(self, mock_get_active):
        mock_get_active.return_value = [
            {"id_deuda": "123", "entidad": "Banco", "monto_total": 500}
        ]
        msg = MagicMock()
        msg.text = "/deudas"
        self.handlers["deudas"](msg)
        mock_get_active.assert_called_once_with(None)
        self.bot_mock.reply_to.assert_called_once()

    @patch("com.handlers.deudas.get_active_debts")
    def test_handle_abonar(self, mock_get_active):
        mock_get_active.return_value = [{"ID_Obligacion": "123", "Nombre": "Deuda 1"}]
        msg = MagicMock()
        msg.text = "/abonar"
        msg.from_user.id = 12345
        self.handlers["abonar"](msg)
        self.bot_mock.reply_to.assert_called_once()

    @patch("com.handlers.deudas.execute_monthly_closing")
    def test_handle_cierre_mensual(self, mock_execute):
        mock_execute.return_value = "drive_123"
        msg = MagicMock()
        msg.text = "/cierre_mensual 9 2026"
        self.handlers["cierre_mensual"](msg)
        mock_execute.assert_called_once_with(9, 2026)
        self.bot_mock.reply_to.assert_called_once()

    @patch("com.handlers.deudas.simulate_project")
    def test_handle_simular(self, mock_simulate):
        mock_simulate.return_value = "proj_123"
        msg = MagicMock()
        msg.text = "/simular 1000 12 Auto_nuevo"
        self.handlers["simular"](msg)
        mock_simulate.assert_called_once_with(1000, 12, "Auto_nuevo")
        self.bot_mock.reply_to.assert_called_once()

    @patch("com.handlers.deudas.approve_project")
    def test_handle_aprobar_proyecto(self, mock_approve):
        msg = MagicMock()
        msg.text = "/aprobar_proyecto proj_123"
        self.handlers["aprobar_proyecto"](msg)
        mock_approve.assert_called_once_with("proj_123")
        self.bot_mock.reply_to.assert_called_once()


if __name__ == "__main__":
    unittest.main()
