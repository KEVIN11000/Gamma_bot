import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock decorators before importing the module
patch('com.core.security.auth_required', lambda bot: lambda f: f).start()
patch('com.core.errors.safe_handler', lambda bot, logger: lambda f: f).start()

import telebot
from telebot.types import Message, CallbackQuery, Chat, User
from com.handlers.avisos import (
    register_avisos_handlers,
    _capturar_frase_aviso_secuencial,
    _procesar_frase_aviso
)

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=telebot.TeleBot)
    
    # Dictionaries to store registered handlers
    bot.registered_message_handlers = {}
    bot.registered_callback_handlers = {}
    
    def message_handler_side_effect(**kwargs):
        def decorator(f):
            if 'commands' in kwargs:
                for cmd in kwargs['commands']:
                    bot.registered_message_handlers[cmd] = f
            return f
        return decorator
        
    def callback_query_handler_side_effect(**kwargs):
        def decorator(f):
            bot.registered_callback_handlers['aviso'] = f
            return f
        return decorator
        
    bot.message_handler.side_effect = message_handler_side_effect
    bot.callback_query_handler.side_effect = callback_query_handler_side_effect
    
    return bot

@pytest.fixture
def mock_gamma_app():
    app = MagicMock()
    app.agente_excel = MagicMock()
    return app

@pytest.fixture
def mock_message():
    msg = MagicMock(spec=Message)
    msg.chat = MagicMock(spec=Chat)
    msg.chat.id = 12345
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 67890
    msg.message_id = 111
    return msg

@pytest.fixture
def mock_call(mock_message):
    call = MagicMock(spec=CallbackQuery)
    call.id = "call_id_1"
    call.message = mock_message
    return call

def get_callback_handlers(bot, app):
    handlers = []
    def cb_handler(**kwargs):
        def dec(f):
            handlers.append((kwargs.get('func'), f))
            return f
        return dec
    bot.callback_query_handler.side_effect = cb_handler
    register_avisos_handlers(bot, app)
    return handlers

def test_comando_aviso_with_args(mock_bot, mock_gamma_app, mock_message):
    register_avisos_handlers(mock_bot, mock_gamma_app)
    handler = mock_bot.registered_message_handlers.get("aviso")
    assert handler is not None
    
    mock_message.text = "/aviso entregar laboratorio mañana"
    
    with patch('com.handlers.avisos._procesar_frase_aviso') as mock_procesar:
        handler(mock_message)
        mock_procesar.assert_called_once_with(mock_message, "entregar laboratorio mañana", mock_bot, mock_gamma_app)

def test_comando_aviso_without_args(mock_bot, mock_gamma_app, mock_message):
    register_avisos_handlers(mock_bot, mock_gamma_app)
    handler = mock_bot.registered_message_handlers.get("aviso")
    
    mock_message.text = "/aviso"
    mock_bot.reply_to.return_value = "reply_msg"
    
    handler(mock_message)
    
    mock_bot.reply_to.assert_called_once()
    mock_bot.register_next_step_handler.assert_called_once()

@patch('com.handlers.avisos.EstadoGestor')
def test_callback_aviso_cancelar(mock_estado, mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    aviso_handler = next(f for func, f in handlers if func(MagicMock(data="aviso_test")))
    
    mock_call.data = "aviso_cancelar"
    aviso_handler(mock_call)
    
    mock_estado.pop.assert_called_once_with(12345)
    mock_bot.edit_message_text.assert_called_once()
    assert "cancelado" in mock_bot.edit_message_text.call_args[0][0]

@patch('com.handlers.avisos.EstadoGestor')
def test_callback_aviso_confirmar_expired(mock_estado, mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    aviso_handler = next(f for func, f in handlers if func(MagicMock(data="aviso_test")))
    
    mock_call.data = "aviso_confirmar"
    mock_estado.get.return_value = None
    
    aviso_handler(mock_call)
    
    mock_bot.edit_message_text.assert_called_once()
    assert "Expiró" in mock_bot.edit_message_text.call_args[0][0]

@patch('com.handlers.avisos.EstadoGestor')
def test_callback_aviso_confirmar_success(mock_estado, mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    aviso_handler = next(f for func, f in handlers if func(MagicMock(data="aviso_test")))
    
    mock_call.data = "aviso_confirmar"
    mock_estado.get.return_value = {"titulo": "Test", "fecha": "2023-10-10"}
    mock_gamma_app.agente_excel.guardar_aviso_calendar.return_value = "Guardado OK"
    
    aviso_handler(mock_call)
    
    mock_gamma_app.agente_excel.guardar_aviso_calendar.assert_called_once_with({"titulo": "Test", "fecha": "2023-10-10"})
    mock_estado.pop.assert_called_once_with(12345)
    assert mock_bot.edit_message_text.call_count == 2
    assert "Guardado OK" in mock_bot.edit_message_text.call_args[0][0]

@patch('com.handlers.avisos.EstadoGestor')
def test_callback_aviso_exception(mock_estado, mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    aviso_handler = next(f for func, f in handlers if func(MagicMock(data="aviso_test")))
    
    mock_call.data = "aviso_confirmar"
    mock_estado.get.side_effect = Exception("Test Exception")
    
    aviso_handler(mock_call)
    mock_bot.send_message.assert_called_once()
    assert "Test Exception" in mock_bot.send_message.call_args[0][1]

def test_comando_avisos_empty(mock_bot, mock_gamma_app, mock_message):
    register_avisos_handlers(mock_bot, mock_gamma_app)
    handler = mock_bot.registered_message_handlers.get("avisos")
    
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.return_value = []
    
    handler(mock_message)
    
    mock_bot.reply_to.assert_called_once()
    assert "No tenés ningún aviso" in mock_bot.reply_to.call_args[0][1]

def test_comando_avisos_with_items(mock_bot, mock_gamma_app, mock_message):
    register_avisos_handlers(mock_bot, mock_gamma_app)
    handler = mock_bot.registered_message_handlers.get("avisos")
    
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.return_value = [
        {"titulo": "Aviso 1", "fecha_evento": "2023-10-10 10:00"},
        {"titulo": "Aviso 2", "fecha_evento": "2023-10-11 11:00"},
        {"titulo": "Aviso 3", "fecha_evento": "2023-10-12 12:00"}
    ]
    
    handler(mock_message)
    
    mock_bot.reply_to.assert_called_once()
    args, kwargs = mock_bot.reply_to.call_args
    assert "Aviso 1" in args[1]
    assert "Aviso 2" in args[1]
    assert "Aviso 3" in args[1]
    assert "reply_markup" in kwargs

def test_comando_avisos_telegram_exception(mock_bot, mock_gamma_app, mock_message):
    register_avisos_handlers(mock_bot, mock_gamma_app)
    handler = mock_bot.registered_message_handlers.get("avisos")
    
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.side_effect = telebot.apihelper.ApiTelegramException('metod', 'result', {'error_code': 400, 'description': 'Bad Request'})
    
    handler(mock_message)
    mock_bot.reply_to.assert_called_once()
    assert "error de conexión" in mock_bot.reply_to.call_args[0][1]

def test_comando_avisos_general_exception(mock_bot, mock_gamma_app, mock_message):
    register_avisos_handlers(mock_bot, mock_gamma_app)
    handler = mock_bot.registered_message_handlers.get("avisos")
    
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.side_effect = Exception("General Error")
    
    handler(mock_message)
    mock_bot.reply_to.assert_called_once()
    assert "General Error" in mock_bot.reply_to.call_args[0][1]

def test_callback_borrar_aviso_success_and_empty(mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    borrar_handler = next(f for func, f in handlers if func(MagicMock(data="borrar_test")))
    
    mock_call.data = "borrar_0"
    lista_inicial = [
        {"id": "id0", "titulo": "Aviso 0", "fecha_evento": "2023-10-10 10:00"}
    ]
    # Se borra y la lista queda vacía
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.side_effect = [
        lista_inicial,
        []
    ]
    mock_gamma_app.agente_excel.eliminar_aviso_calendar.return_value = True
    
    borrar_handler(mock_call)
    
    mock_bot.send_message.assert_called_once()
    assert "fue eliminado correctamente" in mock_bot.send_message.call_args[0][1]
    mock_bot.edit_message_text.assert_called_once()
    assert "No te quedan más avisos" in mock_bot.edit_message_text.call_args[0][0]

def test_callback_borrar_aviso_failure(mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    borrar_handler = next(f for func, f in handlers if func(MagicMock(data="borrar_test")))
    
    mock_call.data = "borrar_0"
    lista_inicial = [{"id": "id0", "titulo": "Aviso 0", "fecha_evento": "2023-10-10"}]
    
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.return_value = lista_inicial
    mock_gamma_app.agente_excel.eliminar_aviso_calendar.return_value = False
    
    borrar_handler(mock_call)
    
    mock_bot.send_message.assert_called_once()
    assert "error al eliminar" in mock_bot.send_message.call_args[0][1]

def test_callback_borrar_aviso_out_of_bounds(mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    borrar_handler = next(f for func, f in handlers if func(MagicMock(data="borrar_test")))
    
    mock_call.data = "borrar_5"
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.return_value = []
    
    borrar_handler(mock_call)
    mock_bot.send_message.assert_called_once()
    assert "ya no existe" in mock_bot.send_message.call_args[0][1]

def test_callback_borrar_aviso_exception(mock_bot, mock_gamma_app, mock_call):
    handlers = get_callback_handlers(mock_bot, mock_gamma_app)
    borrar_handler = next(f for func, f in handlers if func(MagicMock(data="borrar_test")))
    
    mock_call.data = "borrar_0"
    mock_gamma_app.agente_excel.obtener_lista_avisos_calendar.side_effect = Exception("Test Error")
    
    borrar_handler(mock_call)
    mock_bot.send_message.assert_called_once()
    assert "Test Error" in mock_bot.send_message.call_args[0][1]

@patch('com.handlers.avisos.verificar_usuario_manual')
def test_capturar_frase_aviso_secuencial_invalid_not_verified(mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = False
    _capturar_frase_aviso_secuencial(mock_message, mock_bot, mock_gamma_app)
    # Shouldn't do anything
    mock_bot.reply_to.assert_not_called()

@patch('com.handlers.avisos.verificar_usuario_manual')
def test_capturar_frase_aviso_secuencial_invalid_text(mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = True
    mock_message.text = "/comando_invalido"
    
    _capturar_frase_aviso_secuencial(mock_message, mock_bot, mock_gamma_app)
    
    mock_bot.reply_to.assert_called_once()
    assert "Operación cancelada" in mock_bot.reply_to.call_args[0][1]

@patch('com.handlers.avisos.verificar_usuario_manual')
@patch('com.handlers.avisos._procesar_frase_aviso')
def test_capturar_frase_aviso_secuencial_valid(mock_procesar, mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = True
    mock_message.text = "entregar tp"
    
    _capturar_frase_aviso_secuencial(mock_message, mock_bot, mock_gamma_app)
    
    mock_procesar.assert_called_once_with(mock_message, "entregar tp", mock_bot, mock_gamma_app)

@patch('com.handlers.avisos.AIService')
@patch('com.handlers.avisos.EstadoGestor')
def test_procesar_frase_aviso_success(mock_estado, mock_aiservice, mock_bot, mock_gamma_app, mock_message):
    mock_msg_espera = MagicMock()
    mock_msg_espera.message_id = 999
    mock_bot.send_message.return_value = mock_msg_espera
    
    datos_ia = {
        "titulo": "Entregar tp",
        "fecha": "Mañana",
        "hora": "10:00"
    }
    mock_aiservice.interpretar_frase_con_ia.return_value = datos_ia
    
    _procesar_frase_aviso(mock_message, "entregar tp mañana", mock_bot, mock_gamma_app)
    
    mock_aiservice.interpretar_frase_con_ia.assert_called_once_with("entregar tp mañana")
    mock_estado.set.assert_called_once_with(12345, datos_ia)
    mock_bot.edit_message_text.assert_called_once()
    args, kwargs = mock_bot.edit_message_text.call_args
    assert "Previsualización" in args[0]
    assert kwargs.get("reply_markup") is not None

@patch('com.handlers.avisos.AIService')
def test_procesar_frase_aviso_error(mock_aiservice, mock_bot, mock_gamma_app, mock_message):
    mock_msg_espera = MagicMock()
    mock_msg_espera.message_id = 999
    mock_bot.send_message.return_value = mock_msg_espera
    
    mock_aiservice.interpretar_frase_con_ia.return_value = {"error": "No entendí"}
    
    _procesar_frase_aviso(mock_message, "frase rara", mock_bot, mock_gamma_app)
    
    mock_bot.edit_message_text.assert_called_once()
    assert "No entendí" in mock_bot.edit_message_text.call_args[0][0]
