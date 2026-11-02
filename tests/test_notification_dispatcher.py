import pytest
from services.notification_dispatcher import NotificationDispatcher
from adapters.notifications.mock_adapter import MockNotificationAdapter


def test_dispatcher_register_and_has_channel():
    dispatcher = NotificationDispatcher(default_channel="telegram")
    telegram_mock = MockNotificationAdapter()
    whatsapp_mock = MockNotificationAdapter()

    assert not dispatcher.has_channel("telegram")
    assert not dispatcher.has_channel("whatsapp")

    dispatcher.register_adapter("Telegram", telegram_mock)
    dispatcher.register_adapter("whatsapp", whatsapp_mock)

    assert dispatcher.has_channel("telegram")
    assert dispatcher.has_channel("TELEGRAM")
    assert dispatcher.has_channel("whatsapp")
    assert not dispatcher.has_channel("mobile")
    assert set(dispatcher.registered_channels) == {"telegram", "whatsapp"}


def test_dispatcher_register_invalid_type():
    dispatcher = NotificationDispatcher()
    with pytest.raises(TypeError, match="Adapter must implement INotificationPort"):
        dispatcher.register_adapter("telegram", "not_an_adapter")  # type: ignore[arg-type]


def test_dispatcher_get_adapter_and_default():
    dispatcher = NotificationDispatcher(default_channel="telegram")
    telegram_mock = MockNotificationAdapter()
    dispatcher.register_adapter("telegram", telegram_mock)

    # By explicit name
    assert dispatcher.get_adapter("telegram") is telegram_mock
    assert dispatcher.get_adapter("  TELEGRAM ") is telegram_mock

    # By default (None or empty)
    assert dispatcher.get_adapter(None) is telegram_mock
    assert dispatcher.get_adapter("") is telegram_mock
    assert dispatcher.get_adapter() is telegram_mock


def test_dispatcher_get_unregistered_channel_raises():
    dispatcher = NotificationDispatcher(default_channel="telegram")
    with pytest.raises(
        KeyError, match="No notification adapter registered for channel 'telegram'"
    ):
        dispatcher.get_adapter("telegram")

    dispatcher.register_adapter("whatsapp", MockNotificationAdapter())
    with pytest.raises(
        KeyError, match="No notification adapter registered for channel 'telegram'"
    ):
        dispatcher.get_adapter()


def test_dispatcher_send_message_routes_to_channel():
    dispatcher = NotificationDispatcher(default_channel="telegram")
    telegram_mock = MockNotificationAdapter()
    whatsapp_mock = MockNotificationAdapter()
    dispatcher.register_adapter("telegram", telegram_mock)
    dispatcher.register_adapter("whatsapp", whatsapp_mock)

    # Send using default
    ok = dispatcher.send_message("user_tg", "Mensaje TG", parse_mode="Markdown")
    assert ok is True
    assert len(telegram_mock.sent_messages) == 1
    assert telegram_mock.sent_messages[0].recipient_id == "user_tg"
    assert telegram_mock.sent_messages[0].message == "Mensaje TG"
    assert len(whatsapp_mock.sent_messages) == 0

    # Send specifying whatsapp
    ok2 = dispatcher.send_message("+595981123456", "Mensaje WA", channel="whatsapp")
    assert ok2 is True
    assert len(whatsapp_mock.sent_messages) == 1
    assert whatsapp_mock.sent_messages[0].recipient_id == "+595981123456"
    assert whatsapp_mock.sent_messages[0].message == "Mensaje WA"


def test_dispatcher_send_document_routes_to_channel():
    dispatcher = NotificationDispatcher(default_channel="telegram")
    telegram_mock = MockNotificationAdapter()
    dispatcher.register_adapter("telegram", telegram_mock)

    ok = dispatcher.send_document(
        recipient_id="user_1",
        document_path="/tmp/balance.pdf",
        caption="Balance Mensual",
        visible_file_name="balance.pdf",
    )
    assert ok is True
    assert len(telegram_mock.sent_documents) == 1
    doc = telegram_mock.sent_documents[0]
    assert doc.recipient_id == "user_1"
    assert doc.document_path == "/tmp/balance.pdf"
    assert doc.caption == "Balance Mensual"
    assert doc.visible_file_name == "balance.pdf"


def test_dispatcher_unregister_channel():
    dispatcher = NotificationDispatcher()
    mock_adapter = MockNotificationAdapter()
    dispatcher.register_adapter("mobile", mock_adapter)
    assert dispatcher.has_channel("mobile")

    removed = dispatcher.unregister_adapter("mobile")
    assert removed is True
    assert not dispatcher.has_channel("mobile")

    removed_again = dispatcher.unregister_adapter("mobile")
    assert removed_again is False


def test_dispatcher_change_default_channel():
    dispatcher = NotificationDispatcher(default_channel="telegram")
    assert dispatcher.default_channel == "telegram"
    dispatcher.default_channel = "whatsapp"
    assert dispatcher.default_channel == "whatsapp"
