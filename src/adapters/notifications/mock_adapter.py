from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ports.notification_port import INotificationPort


@dataclass
class SentMessageRecord:
    """Record of an in-memory sent message."""

    recipient_id: str
    message: str
    parse_mode: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SentDocumentRecord:
    """Record of an in-memory sent document."""

    recipient_id: str
    document_path: str
    caption: str = ""
    visible_file_name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class MockNotificationAdapter(INotificationPort):
    """In-memory mock adapter for deterministic testing and isolation."""

    def __init__(
        self,
        should_fail: bool = False,
        fail_error: Optional[Exception] = None,
    ) -> None:
        self.sent_messages: List[SentMessageRecord] = []
        self.sent_documents: List[SentDocumentRecord] = []
        self.should_fail = should_fail
        self.fail_error = fail_error or RuntimeError("Simulated notification failure")

    def send_message(
        self,
        recipient_id: str,
        message: str,
        parse_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        if self.should_fail:
            raise self.fail_error
        self.sent_messages.append(
            SentMessageRecord(
                recipient_id=str(recipient_id),
                message=message,
                parse_mode=parse_mode,
                extra=kwargs,
            )
        )
        return True

    def send_document(
        self,
        recipient_id: str,
        document_path: str,
        caption: str = "",
        visible_file_name: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        if self.should_fail:
            raise self.fail_error
        self.sent_documents.append(
            SentDocumentRecord(
                recipient_id=str(recipient_id),
                document_path=str(document_path),
                caption=caption,
                visible_file_name=visible_file_name,
                extra=kwargs,
            )
        )
        return True

    def clear(self) -> None:
        """Clears all recorded messages and documents."""
        self.sent_messages.clear()
        self.sent_documents.clear()
