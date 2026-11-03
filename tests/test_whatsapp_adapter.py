import base64
from unittest.mock import MagicMock
import pytest
from ports.notification_port import INotificationPort
from adapters.notifications.whatsapp_adapter import WhatsAppNotificationAdapter
import requests


def test_whatsapp_adapter_implements_interface():
    """Verifies that WhatsAppNotificationAdapter satisfies INotificationPort."""
    adapter = WhatsAppNotificationAdapter()
    assert isinstance(adapter, INotificationPort)


def test_whatsapp_adapter_send_message_success():
    """Verifies text message dispatch with header and payload formatting."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_session.post.return_value = mock_response

    adapter = WhatsAppNotificationAdapter(
        api_url="http://wa-gateway:8080",
        api_key="my_secret_token",
        instance_name="gamma_instance",
        session=mock_session,
    )

    ok = adapter.send_message(
        recipient_id="0981 123 456",
        message="Hola desde WhatsApp!",
    )
    assert ok is True

    mock_session.post.assert_called_once()
    url, kwargs = mock_session.post.call_args[0][0], mock_session.post.call_args[1]

    assert url == "http://wa-gateway:8080/message/sendText/gamma_instance"
    assert kwargs["headers"]["apikey"] == "my_secret_token"
    assert kwargs["headers"]["Authorization"] == "Bearer my_secret_token"
    assert kwargs["json"] == {
        "number": "595981123456",
        "text": "Hola desde WhatsApp!",
    }


def test_whatsapp_adapter_send_message_group_jid():
    """Verifies that group JIDs are preserved without stripping."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_session.post.return_value = mock_response

    adapter = WhatsAppNotificationAdapter(session=mock_session)
    group_id = "120363041234567890@g.us"

    ok = adapter.send_message(recipient_id=group_id, message="Aviso al grupo")
    assert ok is True

    json_payload = mock_session.post.call_args[1]["json"]
    assert json_payload["number"] == group_id
    assert json_payload["text"] == "Aviso al grupo"


def test_whatsapp_adapter_send_message_http_error():
    """Verifies exception handling when the gateway returns HTTP 500."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Gateway internal error"
    mock_session.post.return_value = mock_response

    adapter = WhatsAppNotificationAdapter(session=mock_session)

    with pytest.raises(RuntimeError, match="WhatsApp API HTTP 500"):
        adapter.send_message("0981 123 456", "Fallo")

    # With raise_on_error=False
    ok = adapter.send_message("0981 123 456", "Fallo", raise_on_error=False)
    assert ok is False


def test_whatsapp_adapter_send_message_network_error():
    """Verifies behavior when requests raises a network/timeout exception."""
    mock_session = MagicMock()
    mock_session.post.side_effect = requests.exceptions.ConnectTimeout("Timeout")

    adapter = WhatsAppNotificationAdapter(session=mock_session)

    with pytest.raises(requests.exceptions.ConnectTimeout):
        adapter.send_message("0981 123 456", "Timeout")

    ok = adapter.send_message("0981 123 456", "Timeout", raise_on_error=False)
    assert ok is False


def test_whatsapp_adapter_send_document_success(tmp_path):
    """Verifies document delivery with base64 encoding and metadata."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_session.post.return_value = mock_response

    test_pdf = tmp_path / "balance_test.pdf"
    content = b"%PDF-1.4 binary content test"
    test_pdf.write_bytes(content)

    adapter = WhatsAppNotificationAdapter(
        api_url="https://api.evolution.io/",
        instance_name="my_bot",
        session=mock_session,
    )

    ok = adapter.send_document(
        recipient_id="+595 981 555 444",
        document_path=str(test_pdf),
        caption="Balance Anual",
        visible_file_name="balance_2026.pdf",
    )
    assert ok is True

    url, kwargs = mock_session.post.call_args[0][0], mock_session.post.call_args[1]
    assert url == "https://api.evolution.io/message/sendMedia/my_bot"

    payload = kwargs["json"]
    assert payload["number"] == "595981555444"
    assert payload["mediatype"] == "document"
    assert payload["mimetype"] == "application/pdf"
    assert payload["caption"] == "Balance Anual"
    assert payload["fileName"] == "balance_2026.pdf"

    # Decode and compare base64
    decoded = base64.b64decode(payload["media"])
    assert decoded == content


def test_whatsapp_adapter_send_document_file_not_found():
    """Verifies FileNotFoundError when document file is missing."""
    adapter = WhatsAppNotificationAdapter()

    with pytest.raises(FileNotFoundError):
        adapter.send_document("0981 123 456", "non_existent_file.pdf")

    ok = adapter.send_document(
        "0981 123 456", "non_existent_file.pdf", raise_on_error=False
    )
    assert ok is False
