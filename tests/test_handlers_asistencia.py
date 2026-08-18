import pytest
from unittest.mock import MagicMock, patch

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, Chat, User

from com.handlers.asistencia import register_asistencia_handlers


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("com.core.security.get_authorized_users", return_value={123}):
        yield


@pytest.fixture
def mock_bot():
    return MagicMock(spec=TeleBot)


@pytest.fixture
def mock_gamma_app():
    return MagicMock()


@pytest.fixture
def registered_handlers(mock_bot, mock_gamma_app):
    handlers = {}
    
    def mock_message_handler(**kwargs):
        def decorator(func):
            commands = kwargs.get("commands", [])
            for cmd in commands:
                handlers[f"cmd_{cmd}"] = func
            return func
        return decorator

    def mock_callback_query_handler(func=None, **kwargs):
        def decorator(f):
            if "callbacks" not in handlers:
                handlers["callbacks"] = []
            condition = func if func is not None else kwargs.get("func")
            handlers["callbacks"].append((condition, f))
            return f
        return decorator

    mock_bot.message_handler = mock_message_handler
    mock_bot.callback_query_handler = mock_callback_query_handler
    
    register_asistencia_handlers(mock_bot, mock_gamma_app)
    return handlers


def create_message(text, user_id=123):
    msg = MagicMock(spec=Message)
    msg.text = text
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = 456
    msg.message_id = 789
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = user_id
    msg.from_user.username = "testuser"
    msg.from_user.first_name = "Test"
    msg.from_user.last_name = "User"
    return msg


def create_callback(data, message=None, user_id=123):
    call = MagicMock(spec=CallbackQuery)
    call.id = "call123"
    call.data = data
    if not message:
        message = create_message("", user_id=user_id)
    call.message = message
    call.from_user = message.from_user
    return call


def get_callback_handler(registered_handlers, data):
    for cond, func in registered_handlers.get("callbacks", []):
        if cond(MagicMock(data=data)):
            return func
    raise ValueError(f"No handler found for callback data: {data}")


def test_comando_marcar(registered_handlers, mock_bot):
    handler = registered_handlers["cmd_marcar"]
    msg = create_message("/marcar")
    handler(msg)
    mock_bot.send_message.assert_called_once()
    assert "¿Qué tipo de registro querés hacer hoy?" in mock_bot.send_message.call_args[0][1]


@patch("time.time", return_value=1000000000)
def test_callback_marcado(mock_time, registered_handlers, mock_bot, mock_gamma_app):
    handler = get_callback_handler(registered_handlers, "marcar_normal")
    
    # expired
    call = create_callback("marcar_normal")
    call.message.date = 0
    handler(call)
    mock_bot.answer_callback_query.assert_called_with(call.id, "❌ Este botón ha expirado.", show_alert=True)
    
    # valid - normal
    call.message.date = 1000000000
    mock_bot.reset_mock()
    mock_gamma_app.agente_excel.ejecutar_marcado_para_bot.return_value = "Marcado listo"
    handler(call)
    mock_gamma_app.agente_excel.ejecutar_marcado_para_bot.assert_called_with(modo="normal")
    mock_bot.edit_message_text.assert_called_with("Marcado listo", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    # valid - directo
    call = create_callback("marcar_directo")
    call.message.date = 1000000000
    mock_bot.reset_mock()
    handler(call)
    mock_gamma_app.agente_excel.ejecutar_marcado_para_bot.assert_called_with(modo="directo")


def test_comando_marcar_materia(registered_handlers, mock_bot, mock_gamma_app):
    handler = registered_handlers["cmd_marcar_materia"]
    msg = create_message("/marcar_materia")
    reply_msg = MagicMock()
    reply_msg.message_id = 999
    mock_bot.reply_to.return_value = reply_msg
    mock_gamma_app.agente_materias.marcar_asistencia.return_value = "Asistencia en materia"
    
    handler(msg)
    mock_bot.reply_to.assert_called_once()
    mock_bot.edit_message_text.assert_called_with("Asistencia en materia", msg.chat.id, 999, parse_mode="Markdown")


def test_comando_cierre(registered_handlers, mock_bot):
    handler = registered_handlers["cmd_cierre"]
    msg = create_message("/cierre")
    handler(msg)
    mock_bot.send_message.assert_called_once()
    assert "¿Ejecutar el cierre de período?" in mock_bot.send_message.call_args[0][1]


@patch("time.time", return_value=1000000000)
@patch("com.handlers.asistencia.generar_y_enviar_reporte")
def test_callback_cierre(mock_generar_reporte, mock_time, registered_handlers, mock_bot, mock_gamma_app):
    handler = get_callback_handler(registered_handlers, "cierre_confirmar")
    
    # expired
    call = create_callback("cierre_cancelar")
    call.message.date = 0
    handler(call)
    mock_bot.answer_callback_query.assert_called_with(call.id, "❌ Este botón ha expirado.", show_alert=True)
    
    # valid
    call.message.date = 1000000000
    mock_bot.reset_mock()
    handler(call)
    mock_bot.edit_message_text.assert_called_with("❌ Cierre cancelado.", call.message.chat.id, call.message.message_id)
    
    call.data = "cierre_confirmar"
    mock_bot.reset_mock()
    mock_gamma_app.agente_excel.ejecutar_cierre_periodo_manual.return_value = "Cierre OK"
    handler(call)
    mock_bot.send_message.assert_any_call(call.message.chat.id, "Cierre OK", parse_mode="Markdown")
    
    call.data = "cierre_descuento_no"
    mock_bot.reset_mock()
    handler(call)
    mock_generar_reporte.assert_called_with(mock_bot, mock_gamma_app, call.message, descuento=0)

    call.data = "cierre_descuento_si"
    mock_bot.reset_mock()
    handler(call)
    mock_bot.register_next_step_handler.assert_called_once()


@patch("com.handlers.asistencia.iniciar_flujo_reporte_horas")
@patch("com.handlers.asistencia.generar_y_enviar_reporte_financiero")
def test_comando_reporte(mock_financiero, mock_horas, registered_handlers, mock_bot, mock_gamma_app):
    handler = registered_handlers["cmd_reporte"]
    
    msg = create_message("reporte horas")
    handler(msg)
    mock_horas.assert_called_once_with(msg, mock_bot, mock_gamma_app)
    
    msg = create_message("reporte finanzas")
    handler(msg)
    mock_financiero.assert_called_once_with(mock_bot, mock_gamma_app, msg)
    
    msg = create_message("/reporte")
    handler(msg)
    mock_bot.reply_to.assert_called_once()


@patch("com.handlers.asistencia.iniciar_flujo_reporte_horas")
@patch("com.handlers.asistencia.generar_y_enviar_reporte_financiero")
@patch("com.handlers.asistencia.generar_y_enviar_reporte_por_hoja")
@patch("com.handlers.asistencia.EstadoGestor")
def test_callback_reporte(mock_estado, mock_por_hoja, mock_financiero, mock_horas, registered_handlers, mock_bot, mock_gamma_app):
    handler = get_callback_handler(registered_handlers, "reporte_cancelar")
    
    call = create_callback("reporte_cancelar")
    handler(call)
    mock_bot.edit_message_text.assert_called_with("❌ Operación cancelada.", call.message.chat.id, call.message.message_id)
    
    call.data = "reporte_tipo_horas"
    handler(call)
    mock_horas.assert_called_once_with(call.message, mock_bot, mock_gamma_app, is_callback=True)
    
    call.data = "reporte_tipo_finanzas"
    handler(call)
    mock_financiero.assert_called_once_with(mock_bot, mock_gamma_app, call.message, is_callback=True)
    
    call.data = "reporte_hoja_TestHoja"
    mock_bot.reset_mock()
    handler(call)
    mock_estado.set.assert_called_with(f"reporte_{call.message.chat.id}", "TestHoja")
    mock_bot.edit_message_text.assert_called_once()

    call.data = "reporte_desc_no"
    mock_estado.pop.return_value = "TestHoja"
    handler(call)
    mock_por_hoja.assert_called_once_with(mock_bot, mock_gamma_app, call.message, "TestHoja", descuento=0)
    
    # Test session expired
    call.data = "reporte_desc_no"
    mock_estado.pop.return_value = None
    mock_bot.reset_mock()
    handler(call)
    mock_bot.edit_message_text.assert_called_with("❌ Sesión expirada. Ejecutá /reporte de nuevo.", call.message.chat.id, call.message.message_id)

    call.data = "reporte_desc_si"
    mock_bot.reset_mock()
    handler(call)
    mock_bot.register_next_step_handler.assert_called_once()
