from unittest.mock import MagicMock, patch
import pytest
from com.core.utils import (
    _load_pending,
    _save_pending,
    eliminar_mensaje_seguro,
    limpiar_menus_expirados,
    remover_teclado_inline,
    reply_with_expiration,
)


@pytest.fixture
def temp_pending_file(tmp_path):
    file_path = tmp_path / "pending_deletions.json"
    with patch("com.core.utils.PENDING_FILE", str(file_path)):
        yield str(file_path)


def test_load_save_pending(temp_pending_file):
    assert _load_pending() == {}
    _save_pending({"123_456": 1000})
    assert _load_pending() == {"123_456": 1000}

    # Test corrupted file
    with open(temp_pending_file, "w") as f:
        f.write("invalid json")
    assert _load_pending() == {}


@patch("time.time")
def test_limpiar_menus_expirados(mock_time, temp_pending_file):
    mock_bot = MagicMock()
    mock_time.return_value = 2000
    _save_pending({"1_10": 1000, "1_20": 3000})  # expired  # valid

    limpiar_menus_expirados(mock_bot)

    mock_bot.delete_message.assert_called_once_with("1", "10")
    data = _load_pending()
    assert "1_10" not in data
    assert "1_20" in data


@patch("threading.Timer")
@patch("time.time")
def test_reply_with_expiration(mock_time, mock_timer, temp_pending_file):
    mock_bot = MagicMock()
    mock_time.return_value = 1000
    mock_msg = MagicMock()
    mock_msg.chat.id = 123
    mock_msg.message_id = 456
    mock_bot.send_message.return_value = mock_msg

    reply_with_expiration(mock_bot, 123, "Test message", timeout=30)

    mock_bot.send_message.assert_called_once_with(123, "Test message")
    data = _load_pending()
    assert "123_456" in data
    assert data["123_456"] == 1030

    mock_timer.assert_called_once()
    timeout_arg, delete_task = mock_timer.call_args[0]
    assert timeout_arg == 30

    # test the timer callback
    delete_task()
    mock_bot.delete_message.assert_called_once_with(123, 456)
    data = _load_pending()
    assert "123_456" not in data


def test_eliminar_mensaje_seguro():
    mock_bot = MagicMock()
    # Caso 1: Eliminación exitosa
    assert eliminar_mensaje_seguro(mock_bot, 123, 456) is True
    mock_bot.delete_message.assert_called_with(123, 456)

    # Caso 2: Manejo de mensaje ya eliminado (silencioso)
    mock_bot.delete_message.side_effect = Exception(
        "Bad Request: message to delete not found"
    )
    assert eliminar_mensaje_seguro(mock_bot, 123, 456) is True

    # Caso 3: Manejo de otro error inesperado
    mock_bot.delete_message.side_effect = RuntimeError("Conexión perdida")
    assert eliminar_mensaje_seguro(mock_bot, 123, 456) is False

    # Caso 4: Argumentos inválidos
    assert eliminar_mensaje_seguro(None, 123, 456) is False
    assert eliminar_mensaje_seguro(mock_bot, None, 456) is False
    assert eliminar_mensaje_seguro(mock_bot, 123, -1) is False


def test_remover_teclado_inline():
    mock_bot = MagicMock()
    # Caso 1: Remoción exitosa
    assert remover_teclado_inline(mock_bot, 123, 456) is True
    mock_bot.edit_message_reply_markup.assert_called_with(123, 456, reply_markup=None)

    # Caso 2: Mensaje ya sin teclado o idéntico
    mock_bot.edit_message_reply_markup.side_effect = Exception(
        "Bad Request: message is not modified"
    )
    assert remover_teclado_inline(mock_bot, 123, 456) is True

    # Caso 3: Mensaje no encontrado
    mock_bot.edit_message_reply_markup.side_effect = Exception(
        "Bad Request: message to edit not found"
    )
    assert remover_teclado_inline(mock_bot, 123, 456) is True

    # Caso 4: Error no controlado
    mock_bot.edit_message_reply_markup.side_effect = RuntimeError("Error desconocido")
    assert remover_teclado_inline(mock_bot, 123, 456) is False


@patch("time.time")
def test_limpiar_menus_expirados_estructurado(mock_time, temp_pending_file):
    mock_bot = MagicMock()
    mock_time.return_value = 2000
    # Guardar mezcla de formato legacy (int) y nuevo formato dict con acción
    _save_pending(
        {
            "1_10": 1000,  # legacy vencido -> delete
            "1_20": {
                "chat_id": 1,
                "message_id": 20,
                "expire_at": 1500,
                "action": "clear_markup",
            },  # nuevo vencido
            "1_30": {
                "chat_id": 1,
                "message_id": 30,
                "expire_at": 2500,
                "action": "clear_markup",
            },  # vigente
        }
    )

    procesados = limpiar_menus_expirados(mock_bot)
    assert procesados == 2

    mock_bot.delete_message.assert_called_with("1", "10")
    mock_bot.edit_message_reply_markup.assert_called_with("1", "20", reply_markup=None)

    data = _load_pending()
    assert "1_10" not in data
    assert "1_20" not in data
    assert "1_30" in data


def test_safe_int_validations():
    # Attempt to import from logic.logic first, fallback to logic.financiero
    try:
        from logic.logic import safe_int
    except ImportError:
        from logic.financiero import safe_int

    assert safe_int("") == 0

    # Valida que no crashee con un número con comas y decimales
    res = safe_int("1,500.5")
    assert isinstance(res, int)
    assert safe_int("Gs. 150.000") == 150000
    assert safe_int("150000") == 150000
    assert safe_int("Gs 10.500") == 10500


def test_time_utc3():
    from logic.logic import get_now_py, get_today_py_date, format_timestamp_py

    now = get_now_py()
    assert now.utcoffset().total_seconds() == -10800

    today = get_today_py_date()
    assert today is not None

    ts = format_timestamp_py()
    assert isinstance(ts, str)
