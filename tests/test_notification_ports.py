from unittest.mock import MagicMock
import pytest
from ports.notification_port import INotificationPort
from adapters.notifications.mock_adapter import MockNotificationAdapter
from adapters.notifications.telegram_adapter import TelegramNotificationAdapter


def test_port_abstract_interface_cannot_be_instantiated():
    """Confirms that INotificationPort cannot be instantiated directly."""
    with pytest.raises(TypeError):
        INotificationPort()  # type: ignore[abstract]


def test_incomplete_subclass_cannot_be_instantiated():
    """Confirms that an adapter lacking required abstract methods cannot be instantiated."""

    class IncompleteAdapter(INotificationPort):
        def send_message(self, recipient_id, message, parse_mode=None, **kwargs):
            return True

    with pytest.raises(TypeError):
        IncompleteAdapter()  # type: ignore[abstract]


def test_mock_adapter_send_message():
    """Verifies that MockNotificationAdapter records text messages correctly."""
    adapter = MockNotificationAdapter()
    assert isinstance(adapter, INotificationPort)

    ok = adapter.send_message(
        recipient_id="12345",
        message="Hola mundo",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    assert ok is True
    assert len(adapter.sent_messages) == 1

    record = adapter.sent_messages[0]
    assert record.recipient_id == "12345"
    assert record.message == "Hola mundo"
    assert record.parse_mode == "Markdown"
    assert record.extra == {"disable_web_page_preview": True}


def test_mock_adapter_send_document():
    """Verifies that MockNotificationAdapter records sent documents correctly."""
    adapter = MockNotificationAdapter()

    ok = adapter.send_document(
        recipient_id="99999",
        document_path="/tmp/report.pdf",
        caption="Reporte Financiero",
        visible_file_name="resumen.pdf",
        timeout=30,
    )
    assert ok is True
    assert len(adapter.sent_documents) == 1

    record = adapter.sent_documents[0]
    assert record.recipient_id == "99999"
    assert record.document_path == "/tmp/report.pdf"
    assert record.caption == "Reporte Financiero"
    assert record.visible_file_name == "resumen.pdf"
    assert record.extra == {"timeout": 30}


def test_mock_adapter_error_simulation():
    """Verifies that MockNotificationAdapter raises errors when configured."""
    adapter = MockNotificationAdapter(
        should_fail=True, fail_error=ConnectionError("Red no disponible")
    )

    with pytest.raises(ConnectionError, match="Red no disponible"):
        adapter.send_message("123", "fallo")

    with pytest.raises(ConnectionError, match="Red no disponible"):
        adapter.send_document("123", "/doc.pdf")


def test_mock_adapter_clear():
    """Verifies that clear() wipes all recorded messages and documents."""
    adapter = MockNotificationAdapter()
    adapter.send_message("1", "A")
    adapter.send_document("1", "B.pdf")
    assert len(adapter.sent_messages) == 1
    assert len(adapter.sent_documents) == 1

    adapter.clear()
    assert len(adapter.sent_messages) == 0
    assert len(adapter.sent_documents) == 0


def test_telegram_adapter_send_message_success():
    """Verifies TelegramNotificationAdapter forwards messages to bot."""
    mock_bot = MagicMock()
    adapter = TelegramNotificationAdapter(bot=mock_bot)
    assert isinstance(adapter, INotificationPort)

    ok = adapter.send_message("987654", "Test message", parse_mode="HTML")
    assert ok is True
    mock_bot.send_message.assert_called_once_with(
        987654, "Test message", parse_mode="HTML"
    )


def test_telegram_adapter_invalid_recipient_id():
    """Verifies invalid recipient_id raises ValueError or returns False."""
    mock_bot = MagicMock()
    adapter = TelegramNotificationAdapter(bot=mock_bot)

    with pytest.raises(ValueError, match="Invalid Telegram recipient_id"):
        adapter.send_message("not_an_int", "Test")

    # With raise_on_error=False
    ok = adapter.send_message("not_an_int", "Test", raise_on_error=False)
    assert ok is False


def test_telegram_adapter_send_message_exception():
    """Verifies exception handling when bot.send_message fails."""
    mock_bot = MagicMock()
    mock_bot.send_message.side_effect = RuntimeError("Telegram API timeout")
    adapter = TelegramNotificationAdapter(bot=mock_bot)

    with pytest.raises(RuntimeError, match="Telegram API timeout"):
        adapter.send_message("12345", "Msg")

    ok = adapter.send_message("12345", "Msg", raise_on_error=False)
    assert ok is False


def test_telegram_adapter_send_document_success(tmp_path):
    """Verifies send_document opens, sends, and closes the file descriptor."""
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_bytes(b"%PDF-1.4 sample content")

    mock_bot = MagicMock()
    captured_file_handles = []

    def fake_send_document(chat_id, file_obj, **kwargs):
        captured_file_handles.append(file_obj)
        assert not file_obj.closed
        return True

    mock_bot.send_document.side_effect = fake_send_document
    adapter = TelegramNotificationAdapter(bot=mock_bot)

    ok = adapter.send_document(
        recipient_id="12345",
        document_path=str(test_file),
        caption="Mi Reporte",
        visible_file_name="reporte.pdf",
    )
    assert ok is True
    assert len(captured_file_handles) == 1
    # Check that after send_document returns, the handle is closed!
    assert captured_file_handles[0].closed is True


def test_telegram_adapter_send_document_file_not_found():
    """Verifies FileNotFoundError when document path does not exist."""
    mock_bot = MagicMock()
    adapter = TelegramNotificationAdapter(bot=mock_bot)

    with pytest.raises(FileNotFoundError):
        adapter.send_document("12345", "non_existent_file.pdf")

    ok = adapter.send_document("12345", "non_existent_file.pdf", raise_on_error=False)
    assert ok is False


def test_telegram_adapter_send_document_closes_on_error(tmp_path):
    """Verifies file descriptor is closed even if bot.send_document raises an exception."""
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_bytes(b"%PDF-1.4 sample content")

    mock_bot = MagicMock()
    captured_file_handles = []

    def failing_send_document(chat_id, file_obj, **kwargs):
        captured_file_handles.append(file_obj)
        raise RuntimeError("Network error during document upload")

    mock_bot.send_document.side_effect = failing_send_document
    adapter = TelegramNotificationAdapter(bot=mock_bot)

    with pytest.raises(RuntimeError, match="Network error during document upload"):
        adapter.send_document("12345", str(test_file))

    assert len(captured_file_handles) == 1
    assert captured_file_handles[0].closed is True
