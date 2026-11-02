from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class INotificationPort(ABC):
    """Canonical port interface for agnostic notification dispatch across channels."""

    @abstractmethod
    def send_message(
        self,
        recipient_id: str,
        message: str,
        parse_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Sends a text message to the recipient.

        Args:
            recipient_id: Channel-specific identifier (e.g. Telegram chat_id or WhatsApp phone).
            message: Text body of the message.
            parse_mode: Optional formatting markup (e.g. 'Markdown', 'HTML').
            **kwargs: Additional channel-specific metadata.

        Returns:
            bool: True if delivered or scheduled successfully, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def send_document(
        self,
        recipient_id: str,
        document_path: str,
        caption: str = "",
        visible_file_name: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Sends a file or document to the recipient.

        Args:
            recipient_id: Channel-specific identifier.
            document_path: Local filesystem path to the file.
            caption: Optional text caption accompanying the document.
            visible_file_name: Optional user-facing file name for the attachment.
            **kwargs: Additional channel-specific metadata.

        Returns:
            bool: True if delivered or scheduled successfully, False otherwise.
        """
        raise NotImplementedError
