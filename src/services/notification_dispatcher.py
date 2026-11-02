from __future__ import annotations

from typing import Any, Dict, List, Optional

from logger_config import setup_logger
from ports.notification_port import INotificationPort

logger = setup_logger("notification_dispatcher")


class NotificationDispatcher:
    """Manages multi-channel notification adapters and routes messages/documents to designated channels."""

    def __init__(self, default_channel: str = "telegram") -> None:
        self._adapters: Dict[str, INotificationPort] = {}
        self._default_channel: str = default_channel.lower().strip()

    @property
    def default_channel(self) -> str:
        return self._default_channel

    @default_channel.setter
    def default_channel(self, channel: str) -> None:
        self._default_channel = channel.lower().strip()

    @property
    def registered_channels(self) -> List[str]:
        return list(self._adapters.keys())

    def register_adapter(self, channel: str, adapter: INotificationPort) -> None:
        """Registers an adapter for a given channel name."""
        if not isinstance(adapter, INotificationPort):
            raise TypeError(
                f"Adapter must implement INotificationPort, got {type(adapter).__name__}"
            )
        chan_key = channel.lower().strip()
        self._adapters[chan_key] = adapter
        logger.info(f"Registered notification adapter for channel: '{chan_key}'")

    def unregister_adapter(self, channel: str) -> bool:
        """Removes an adapter for a given channel name if present."""
        chan_key = channel.lower().strip()
        if chan_key in self._adapters:
            del self._adapters[chan_key]
            logger.info(f"Unregistered notification adapter for channel: '{chan_key}'")
            return True
        return False

    def has_channel(self, channel: str) -> bool:
        """Checks if an adapter is registered for the specified channel."""
        return channel.lower().strip() in self._adapters

    def get_adapter(self, channel: Optional[str] = None) -> INotificationPort:
        """Retrieves the adapter for the given channel, or default channel if None/empty."""
        target_channel = channel.lower().strip() if channel else self._default_channel
        if target_channel not in self._adapters:
            available = list(self._adapters.keys())
            raise KeyError(
                f"No notification adapter registered for channel '{target_channel}'. "
                f"Available channels: {available}"
            )
        return self._adapters[target_channel]

    def send_message(
        self,
        recipient_id: str,
        message: str,
        channel: Optional[str] = None,
        parse_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Routes text message dispatch to the designated channel adapter."""
        target_channel = channel.lower().strip() if channel else self._default_channel
        adapter = self.get_adapter(target_channel)
        return adapter.send_message(
            recipient_id=recipient_id,
            message=message,
            parse_mode=parse_mode,
            **kwargs,
        )

    def send_document(
        self,
        recipient_id: str,
        document_path: str,
        channel: Optional[str] = None,
        caption: str = "",
        visible_file_name: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Routes document dispatch to the designated channel adapter."""
        target_channel = channel.lower().strip() if channel else self._default_channel
        adapter = self.get_adapter(target_channel)
        return adapter.send_document(
            recipient_id=recipient_id,
            document_path=document_path,
            caption=caption,
            visible_file_name=visible_file_name,
            **kwargs,
        )
