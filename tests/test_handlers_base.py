import pytest
from unittest.mock import MagicMock, patch, mock_open
import os

# Mock decorators BEFORE importing the module to test, or patch them inside the module
from src.com.handlers.base import _registrar_comandos_menu, register_base_handlers

@pytest.fixture
def bot_mock():
    bot = MagicMock()
    # To capture registered handlers
    bot.registered_handlers = {}
    
    def message_handler_mock(**kwargs):
        def decorator(f):
            for cmd in kwargs.get("commands", []):
                bot.registered_handlers[cmd] = f
            return f
        return decorator
        
    bot.message_handler = message_handler_mock
    return bot

@pytest.fixture
def mock_message():
    msg = MagicMock()
    msg.text = "/start"
    msg.chat.id = 12345
    return msg

@patch.dict(os.environ, {"MODO_DESARROLLADOR": "False"})
def test_registrar_comandos_menu_prod(bot_mock):
    _registrar_comandos_menu(bot_mock)
    bot_mock.set_my_commands.assert_called_once()
    commands_called = bot_mock.set_my_commands.call_args[0][0]
    assert len(commands_called) == 15
    command_names = [c.command for c in commands_called]
    assert "debug" not in command_names

@patch.dict(os.environ, {"MODO_DESARROLLADOR": "True"})
def test_registrar_comandos_menu_dev(bot_mock):
    _registrar_comandos_menu(bot_mock)
    bot_mock.set_my_commands.assert_called_once()
    commands_called = bot_mock.set_my_commands.call_args[0][0]
    assert len(commands_called) == 16
    command_names = [c.command for c in commands_called]
    assert "debug" in command_names

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
def test_comando_debug_prod(mock_safe, mock_auth, bot_mock, mock_message):
    # Mock decorators to pass-through
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers.get("debug")
    assert handler is not None
    
    mock_message.text = "/debug"
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "False"}):
        handler(mock_message)
        bot_mock.reply_to.assert_called_with(
            mock_message,
            "🔒 El comando de depuración está desactivado en este entorno de producción."
        )

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
def test_comando_debug_dev_invalid(mock_safe, mock_auth, bot_mock, mock_message):
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers["debug"]
    
    mock_message.text = "/debug invalid"
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "True"}):
        handler(mock_message)
        bot_mock.reply_to.assert_called_once()
        assert "⚠️ *Comando incorrecto.*" in bot_mock.reply_to.call_args[0][1]

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
@patch("src.com.handlers.base.Path.exists")
def test_comando_debug_dev_app_not_exists(mock_exists, mock_safe, mock_auth, bot_mock, mock_message):
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    mock_exists.return_value = False
    
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers["debug"]
    
    mock_message.text = "/debug app"
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "True"}):
        handler(mock_message)
        bot_mock.reply_to.assert_called_once()
        assert "El archivo" in bot_mock.reply_to.call_args[0][1]

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
@patch("src.com.handlers.base.Path.exists")
def test_comando_debug_dev_app_exists_empty(mock_exists, mock_safe, mock_auth, bot_mock, mock_message):
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    mock_exists.return_value = True
    
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers["debug"]
    
    mock_message.text = "/debug app"
    
    m_open = mock_open(read_data="")
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "True"}), \
         patch("builtins.open", m_open):
        handler(mock_message)
        bot_mock.reply_to.assert_called_once()
        assert "[El archivo existe pero está vacío]" in bot_mock.reply_to.call_args[0][1]

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
@patch("src.com.handlers.base.Path.exists")
def test_comando_debug_dev_app_exists_content(mock_exists, mock_safe, mock_auth, bot_mock, mock_message):
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    mock_exists.return_value = True
    
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers["debug"]
    
    mock_message.text = "/debug server"
    
    m_open = mock_open(read_data="log1\nlog2\n")
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "True"}), \
         patch("builtins.open", m_open):
        handler(mock_message)
        bot_mock.reply_to.assert_called_once()
        assert "log1" in bot_mock.reply_to.call_args[0][1]

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
@patch("src.com.handlers.base._registrar_comandos_menu")
@patch("src.com.handlers.base.Path.exists")
def test_comando_start(mock_exists, mock_registrar, mock_safe, mock_auth, bot_mock, mock_message):
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    mock_exists.return_value = True
    
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers["start"]
    
    mock_message.text = "/start"
    
    m_open = mock_open(read_data="1.0.0")
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "False"}), \
         patch("builtins.open", m_open):
        handler(mock_message)
        
        mock_registrar.assert_called_once_with(bot_mock)
        bot_mock.reply_to.assert_called_once()
        assert "1.0.0" in bot_mock.reply_to.call_args[0][1]
        assert "/debug" not in bot_mock.reply_to.call_args[0][1]

@patch("src.com.handlers.base.auth_required")
@patch("src.com.handlers.base.safe_handler")
@patch("src.com.handlers.base._registrar_comandos_menu")
@patch("src.com.handlers.base.Path.exists")
def test_comando_start_dev(mock_exists, mock_registrar, mock_safe, mock_auth, bot_mock, mock_message):
    mock_auth.return_value = lambda f: f
    mock_safe.return_value = lambda f: f
    mock_exists.return_value = False
    
    register_base_handlers(bot_mock, None)
    handler = bot_mock.registered_handlers["start"]
    
    mock_message.text = "/start"
    
    with patch.dict(os.environ, {"MODO_DESARROLLADOR": "True"}):
        handler(mock_message)
        
        mock_registrar.assert_called_once_with(bot_mock)
        bot_mock.reply_to.assert_called_once()
        assert "1.x" in bot_mock.reply_to.call_args[0][1]
        assert "/debug" in bot_mock.reply_to.call_args[0][1]
