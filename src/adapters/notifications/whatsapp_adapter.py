from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

from logger_config import setup_logger
from ports.notification_port import INotificationPort
import requests
from utils.phone_utils import normalize_phone_number

logger = setup_logger("whatsapp_adapter")


class WhatsAppNotificationAdapter(INotificationPort):
    """Adapter implementing INotificationPort over Evolution API / Meta Cloud WhatsApp gateway."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        instance_name: Optional[str] = None,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_url = (
            api_url or os.getenv("WHATSAPP_API_URL", "http://localhost:8080")
        ).rstrip("/")
        self.api_key = api_key or os.getenv("WHATSAPP_API_KEY", "")
        self.instance_name = (
            instance_name or os.getenv("WHATSAPP_INSTANCE_NAME", "gamma")
        ).strip()
        self.timeout = float(timeout)
        self.session = session or requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["apikey"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _resolve_number(self, recipient_id: str) -> str:
        """Normalizes recipient identifier to clean E.164 digits, preserving group JIDs if present."""
        rec = str(recipient_id).strip()
        if "@g.us" in rec:
            return rec
        return normalize_phone_number(rec, validate=True)

    def send_message(
        self,
        recipient_id: str,
        message: str,
        parse_mode: Optional[str] = None,
        raise_on_error: bool = True,
        **kwargs: Any,
    ) -> bool:
        """Sends a text message via WhatsApp Evolution API.

        Args:
            recipient_id: Destination phone number or WhatsApp JID.
            message: Text message body.
            parse_mode: Ignored or passed to extra options.
            raise_on_error: If True, raises exceptions on HTTP or network failures.
            **kwargs: Extra parameters merged into the payload.

        Returns:
            bool: True if delivered/accepted by gateway, False otherwise.
        """
        try:
            target_number = self._resolve_number(recipient_id)
            endpoint = f"{self.api_url}/message/sendText/{self.instance_name}"
            payload: Dict[str, Any] = {
                "number": target_number,
                "text": message,
            }
            payload.update(kwargs)

            resp = self.session.post(
                endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if resp.status_code not in (200, 201):
                err_msg = (
                    f"WhatsApp API HTTP {resp.status_code} for recipient {recipient_id}: "
                    f"{resp.text}"
                )
                logger.error(err_msg)
                if raise_on_error:
                    raise RuntimeError(err_msg)
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {recipient_id}: {e}")
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
        """Sends a document (PDF) via WhatsApp Evolution API encoded in base64.

        Args:
            recipient_id: Destination phone number or WhatsApp JID.
            document_path: Local path to the file.
            caption: Optional caption for the document.
            visible_file_name: Optional custom filename.
            raise_on_error: If True, raises exceptions on HTTP or network failures.
            **kwargs: Extra parameters merged into the payload.

        Returns:
            bool: True if delivered/accepted by gateway, False otherwise.
        """
        try:
            target_number = self._resolve_number(recipient_id)
            doc_path = Path(document_path)
            if not doc_path.exists():
                raise FileNotFoundError(f"Document not found at path: {document_path}")

            filename = visible_file_name or doc_path.name
            with open(doc_path, "rb") as f:
                raw_bytes = f.read()

            b64_content = base64.b64encode(raw_bytes).decode("utf-8")
            endpoint = f"{self.api_url}/message/sendMedia/{self.instance_name}"

            payload: Dict[str, Any] = {
                "number": target_number,
                "mediatype": "document",
                "mimetype": "application/pdf",
                "caption": caption,
                "media": b64_content,
                "fileName": filename,
            }
            payload.update(kwargs)

            resp = self.session.post(
                endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if resp.status_code not in (200, 201):
                err_msg = (
                    f"WhatsApp API HTTP {resp.status_code} sending document to {recipient_id}: "
                    f"{resp.text}"
                )
                logger.error(err_msg)
                if raise_on_error:
                    raise RuntimeError(err_msg)
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to send WhatsApp document to {recipient_id}: {e}")
            if raise_on_error:
                raise
            return False
