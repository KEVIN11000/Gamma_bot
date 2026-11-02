from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from logger_config import setup_logger
from ports.notification_port import INotificationPort

logger = setup_logger("telegram_adapter")


class TelegramNotificationAdapter(INotificationPort):
    """Adapter implementing INotificationPort over a Telegram bot instance (e.g. telebot)."""

    def __init__(self, bot: Any) -> None:
        self.bot = bot

    def _parse_chat_id(self, recipient_id: Union[str, int]) -> int:
        try:
            return int(recipient_id)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid Telegram recipient_id '{recipient_id}'; must be convertible to int"
            ) from exc

    def send_message(
        self,
        recipient_id: str,
        message: str,
        parse_mode: Optional[str] = None,
        raise_on_error: bool = True,
        **kwargs: Any,
    ) -> bool:
        """Sends a text message through the Telegram bot.

        Args:
            recipient_id: Telegram chat ID (string or int).
            message: Text message content.
            parse_mode: Optional parse mode ('Markdown', 'HTML', etc.).
            raise_on_error: If True, re-raises underlying exceptions for worker retries.
            **kwargs: Extra parameters passed to bot.send_message.

        Returns:
            bool: True if sent successfully, False otherwise.
        """
        try:
            chat_id = self._parse_chat_id(recipient_id)
            call_kwargs: Dict[str, Any] = {}
            if parse_mode is not None:
                call_kwargs["parse_mode"] = parse_mode
            call_kwargs.update(kwargs)

            self.bot.send_message(chat_id, message, **call_kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {recipient_id}: {e}")
            if raise_on_error:
                raise
            return False

    def send_document(
        self,
        recipient_id: str,
        document_path: str,
        caption: str = "",
        visible_file_name: Optional[str] = None,
        raise_on_error: bool = True,
        **kwargs: Any,
    ) -> bool:
        """Sends a document through the Telegram bot, ensuring the file descriptor is closed.

        Args:
            recipient_id: Telegram chat ID (string or int).
            document_path: Local path to the file.
            caption: Optional caption for the document.
            visible_file_name: Optional filename presented to the user.
            raise_on_error: If True, re-raises underlying exceptions for worker retries.
            **kwargs: Extra parameters passed to bot.send_document.

        Returns:
            bool: True if sent successfully, False otherwise.
        """
        try:
            chat_id = self._parse_chat_id(recipient_id)
            doc_file = Path(document_path)
            if not doc_file.exists():
                raise FileNotFoundError(f"Document not found at path: {document_path}")

            call_kwargs: Dict[str, Any] = {}
            if caption:
                call_kwargs["caption"] = caption
            if visible_file_name:
                call_kwargs["visible_file_name"] = visible_file_name
            call_kwargs.update(kwargs)

            with open(doc_file, "rb") as f:
                self.bot.send_document(chat_id, f, **call_kwargs)
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram document to {recipient_id}: {e}")
            if raise_on_error:
                raise
            return False
