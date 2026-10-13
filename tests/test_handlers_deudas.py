import unittest  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

# Mock the decorators BEFORE importing the handlers

patch("com.core.security.auth_required", lambda bot: lambda f: f).start()
patch("com.core.errors.safe_handler", lambda bot, logger: lambda f: f).start()

from com.handlers.deudas import register_deudas_handlers  # noqa: E402
import com.core.states as states  # noqa: E402


class TestDeudasHandlers(unittest.TestCase):
    def setUp(self):
        self.bot_mock = MagicMock()
        self.gamma_app_mock = MagicMock()

        self.handlers = {}
        self.callbacks = []

        def mock_message_handler(**kwargs):
            def decorator(func):
                if "commands" in kwargs:
                    for cmd in kwargs["commands"]:
                        self.handlers[cmd] = func
                return func

            return decorator

        def mock_callback_query_handler(**kwargs):
            def decorator(func):
                self.callbacks.append((kwargs.get("func"), func))
                return func

            return decorator

        self.bot_mock.message_handler = mock_message_handler
        self.bot_mock.callback_query_handler = mock_callback_query_handler

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

    def test_handle_cierre_mensual_interactivo(self):
        msg = MagicMock()
        msg.text = "/cierre_mensual"
        self.handlers["cierre_mensual"](msg)
        self.bot_mock.reply_to.assert_called_once()
        args, kwargs = self.bot_mock.reply_to.call_args
        self.assertIn("Opciones de Cierre Mensual", args[1])
        self.assertIsNotNone(kwargs.get("reply_markup"))

    @patch("com.handlers.deudas.execute_monthly_closing")
    def test_callback_cierre_mensual_actual(self, mock_execute):
        mock_execute.return_value = "drive_123"
        call = MagicMock()
        call.data = "cierre_mensual_actual"
        call.message.chat.id = 12345
        call.message.message_id = 99

        handler_found = None
        for condition, func in self.callbacks:
            if condition and condition(call):
                handler_found = func
                break

        self.assertIsNotNone(handler_found)
        handler_found(call)
        mock_execute.assert_called_once()
        self.bot_mock.edit_message_text.assert_called()

    def test_callback_cierre_mensual_manual(self):
        call = MagicMock()
        call.data = "cierre_mensual_manual"
        call.message.chat.id = 12345
        call.message.message_id = 99

        handler_found = None
        for condition, func in self.callbacks:
            if condition and condition(call):
                handler_found = func
                break

        self.assertIsNotNone(handler_found)
        handler_found(call)
        self.bot_mock.edit_message_text.assert_called()

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

    def test_handle_estrategia_interactivo(self):
        msg = MagicMock()
        msg.text = "/estrategia"
        self.handlers["estrategia"](msg)
        self.bot_mock.reply_to.assert_called_once()
        args, kwargs = self.bot_mock.reply_to.call_args
        self.assertIn("Estrategia de Pago de Deudas", args[1])
        self.assertIsNotNone(kwargs.get("reply_markup"))

    @patch("com.handlers.deudas.proyectar_cola_deudas")
    def test_handle_estrategia_directo(self, mock_proyectar):
        mock_proyectar.return_value = {
            "margen_ataque": 500000,
            "proyeccion": [
                {
                    "nombre": "Tarjeta",
                    "id": "1",
                    "vencida": False,
                    "pago_mensual_proyectado": 100000,
                    "meses_estimados": 5,
                    "fecha_fin": "01/2027",
                }
            ],
        }
        msg = MagicMock()
        msg.text = "/estrategia saldo"
        self.handlers["estrategia"](msg)
        mock_proyectar.assert_called_once_with("saldo")
        self.bot_mock.reply_to.assert_called_once()
        args, _ = self.bot_mock.reply_to.call_args
        self.assertIn("Estrategia de Pago Bola de Nieve", args[1])

    def test_callback_estrategia_sel(self):
        call = MagicMock()
        call.data = "estrategia_sel:saldo"
        call.message.chat.id = 12345
        call.from_user.id = 12345

        handler_found = None
        for condition, func in self.callbacks:
            if condition and condition(call):
                handler_found = func
                break

        self.assertIsNotNone(handler_found)
        handler_found(call)
        self.bot_mock.answer_callback_query.assert_called_once_with(call.id)
        self.bot_mock.process_new_messages.assert_called_once()


if __name__ == "__main__":
    unittest.main()
