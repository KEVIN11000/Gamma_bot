import pytest
import os
import time
from unittest.mock import MagicMock, patch
from com.core.utils import _load_pending, _save_pending, limpiar_menus_expirados, reply_with_expiration

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
    _save_pending({
        "1_10": 1000, # expired
        "1_20": 3000  # valid
    })
    
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
