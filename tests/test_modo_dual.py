from unittest.mock import MagicMock, patch
import pytest

# Mock decorators BEFORE importing handlers
patch("com.core.security.auth_required", lambda bot: lambda f: f).start()
patch("com.core.errors.safe_handler", lambda bot, logger: lambda f: f).start()

from com.handlers.finanzas import register_finanzas_handlers
from com.handlers.deudas import register_deudas_handlers
from com.handlers.base import register_base_handlers
from com.core import states


class MockBot:
    def __init__(self):
        self.handlers = {}
        self.callback_handlers = []
        self.reply_to = MagicMock()
        self.send_message = MagicMock()
        self.edit_message_text = MagicMock()
        self.set_my_commands = MagicMock()

    def message_handler(self, **kwargs):
        def decorator(func):
            if "commands" in kwargs:
                for cmd in kwargs["commands"]:
                    self.handlers[cmd] = func
            elif "func" in kwargs:
                self.handlers[f"func_{len(self.handlers)}"] = (kwargs["func"], func)
            return func

        return decorator

    def callback_query_handler(self, **kwargs):
        def decorator(func):
            if "func" in kwargs:
                self.callback_handlers.append((kwargs["func"], func))
            return func

        return decorator


@pytest.fixture
def bot_mock():
    return MockBot()


@pytest.fixture
def mock_gamma():
    gamma = MagicMock()
    gamma.agente_financiero.registrar_movimiento.return_value = (
        "✅ Gasto registrado en Libro Diario"
    )
    return gamma


@pytest.fixture(autouse=True)
def cleanup():
    states.clear_state(12345)
    states.clear_state(67890)
    yield
    states.clear_state(12345)
    states.clear_state(67890)


def create_message(text, user_id=12345, chat_id=12345):
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = user_id
    msg.chat.id = chat_id
    msg.message_id = 999
    return msg


def test_gasto_modo_directo(bot_mock, mock_gamma):
    register_finanzas_handlers(bot_mock, mock_gamma)

    with patch("logic.ai_service.AIService.procesar_movimiento_con_ia") as mock_ia:
        mock_ia.return_value = {
            "total": 50000,
            "neto": 50000,
            "iva": 0,
            "categoria": "Salud",
            "tipo_movimiento": "Gasto",
        }

        msg = create_message("/gasto 50000 Farmacia")
        bot_mock.handlers["gasto"](msg)

        mock_ia.assert_called_once_with("50000 Farmacia", tipo_movimiento="Gasto")
        mock_gamma.agente_financiero.registrar_movimiento.assert_called_once()
        assert states.has_state(12345) is False


def test_gasto_modo_asistido(bot_mock, mock_gamma):
    register_finanzas_handlers(bot_mock, mock_gamma)

    msg = create_message("/gasto")
    bot_mock.handlers["gasto"](msg)

    assert states.has_state(12345) is True
    state = states.get_state(12345)
    assert state["estado"] == "gasto_paso1"
    bot_mock.reply_to.assert_called_once()
    assert "¿Cuánto fue el gasto?" in bot_mock.reply_to.call_args[0][1]


def test_ingreso_modo_directo(bot_mock, mock_gamma):
    register_finanzas_handlers(bot_mock, mock_gamma)

    with patch("logic.ai_service.AIService.procesar_movimiento_con_ia") as mock_ia:
        mock_ia.return_value = {
            "total": 2000000,
            "neto": 2000000,
            "iva": 0,
            "categoria": "Salario",
            "tipo_movimiento": "Ingreso",
        }

        msg = create_message("/ingreso 2000000 Sueldo")
        bot_mock.handlers["ingreso"](msg)

        mock_ia.assert_called_once_with("2000000 Sueldo", tipo_movimiento="Ingreso")
        mock_gamma.agente_financiero.registrar_movimiento.assert_called_once()
        assert states.has_state(12345) is False


def test_ingreso_modo_asistido(bot_mock, mock_gamma):
    register_finanzas_handlers(bot_mock, mock_gamma)

    msg = create_message("/ingreso")
    bot_mock.handlers["ingreso"](msg)

    assert states.has_state(12345) is True
    state = states.get_state(12345)
    assert state["estado"] == "ingreso_paso1"
    assert "¿Cuánto fue el ingreso?" in bot_mock.reply_to.call_args[0][1]


def test_nueva_deuda_modo_directo(bot_mock, mock_gamma):
    register_deudas_handlers(bot_mock, mock_gamma)

    with patch("com.handlers.deudas.create_debt") as mock_create_debt:
        mock_create_debt.return_value = "deuda-999"

        msg = create_message("/nueva_deuda Banco Auto 5000000 12 15/10/2026")
        bot_mock.handlers["nueva_deuda"](msg)

        mock_create_debt.assert_called_once_with(
            "Banco", "Auto", 5000000, 12, "15/10/2026", dia_vencimiento=0
        )
        assert states.has_state(12345) is False
        assert "deuda-999" in bot_mock.reply_to.call_args[0][1]


def test_nueva_deuda_modo_asistido(bot_mock, mock_gamma):
    register_deudas_handlers(bot_mock, mock_gamma)

    msg = create_message("/nueva_deuda")
    bot_mock.handlers["nueva_deuda"](msg)

    assert states.has_state(12345) is True
    state = states.get_state(12345)
    assert state["estado"] == "NUEVA_DEUDA_P1"
    assert "entidad o acreedor" in bot_mock.reply_to.call_args[0][1]


def test_abonar_modo_directo(bot_mock, mock_gamma):
    register_deudas_handlers(bot_mock, mock_gamma)

    with patch("com.handlers.deudas.register_payment") as mock_pay:
        msg = create_message("/abonar d123 150000 21/09/2026 10%")
        bot_mock.handlers["abonar"](msg)

        mock_pay.assert_called_once_with("d123", 150000, "21/09/2026", tasa_iva="10%")
        assert states.has_state(12345) is False
        assert "150.000" in bot_mock.reply_to.call_args[0][1]


def test_abonar_modo_asistido(bot_mock, mock_gamma):
    register_deudas_handlers(bot_mock, mock_gamma)

    with patch("com.handlers.deudas.get_active_debts") as mock_get:
        mock_get.return_value = [{"ID_Obligacion": "d123", "Nombre": "Prestamo"}]

        msg = create_message("/abonar")
        bot_mock.handlers["abonar"](msg)

        mock_get.assert_called_once()
        bot_mock.reply_to.assert_called_once()
        assert "Selecciona la deuda a abonar" in bot_mock.reply_to.call_args[0][1]


def test_cancelar_global(bot_mock, mock_gamma):
    register_base_handlers(bot_mock, mock_gamma)

    # Set state first
    states.set_state(12345, "gasto_paso2", {"monto": 50000})
    assert states.has_state(12345) is True

    msg = create_message("/cancelar")
    bot_mock.handlers["cancelar"](msg)

    assert states.has_state(12345) is False
    assert "cancelada" in bot_mock.reply_to.call_args[0][1].lower()
