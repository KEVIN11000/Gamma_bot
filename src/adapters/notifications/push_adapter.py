from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union

from logger_config import setup_logger
from ports.notification_port import INotificationPort

logger = setup_logger("push_adapter")

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_STORAGE_FILE = BASE_DIR / "data" / "dispositivos_push.json"


@dataclass
class SentPushRecord:
    recipient_id: str
    message: str
    parse_mode: Optional[str] = None
    title: str = "Gamma Finanzas"
    extra_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class PushNotificationAdapter(INotificationPort):
    """Adapter for sending push notifications and managing registered mobile devices."""

    def __init__(
        self,
        storage_path: Optional[Union[str, Path]] = None,
        fcm_server_key: Optional[str] = None,
        http_client: Optional[Any] = None,
    ) -> None:
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_STORAGE_FILE
        self.fcm_server_key = fcm_server_key or os.getenv("FCM_SERVER_KEY")
        self.http_client = http_client
        self.sent_notifications: List[SentPushRecord] = []
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensures that the directory for the storage file exists."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(
                f"Could not create directory {self.storage_path.parent}: {exc}"
            )

    def _load_devices(self) -> Dict[str, Dict[str, Any]]:
        """Loads devices dictionary from JSON storage."""
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
                return {}
        except Exception as exc:
            logger.warning(
                f"Error loading push devices from {self.storage_path}: {exc}"
            )
            return {}

    def _save_devices(self, devices: Dict[str, Dict[str, Any]]) -> None:
        """Persists devices dictionary to JSON storage with atomic replace."""
        self._ensure_storage_dir()
        temp_path = self.storage_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(devices, f, ensure_ascii=False, indent=2)
            temp_path.replace(self.storage_path)
        except Exception as exc:
            logger.error(f"Error saving push devices to {self.storage_path}: {exc}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def registrar_dispositivo(
        self,
        device_token: str,
        platform: str = "android",
        alias_usuario: Optional[str] = "default",
    ) -> Dict[str, Any]:
        """Registers or updates a push device token idempotently."""
        token_clean = device_token.strip()
        if not token_clean:
            raise ValueError("El device_token no puede estar vacío.")

        devices = self._load_devices()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if token_clean in devices:
            devices[token_clean]["platform"] = platform
            devices[token_clean]["alias_usuario"] = alias_usuario or "default"
            devices[token_clean]["actualizado_at"] = now_iso
            devices[token_clean]["activo"] = True
            logger.info(
                f"Push device token updated: ...{token_clean[-8:]} ({platform})"
            )
        else:
            devices[token_clean] = {
                "device_token": token_clean,
                "platform": platform,
                "alias_usuario": alias_usuario or "default",
                "registrado_at": now_iso,
                "actualizado_at": now_iso,
                "activo": True,
            }
            logger.info(
                f"New push device token registered: ...{token_clean[-8:]} ({platform})"
            )

        self._save_devices(devices)
        return devices[token_clean]

    def desregistrar_dispositivo(self, device_token: str) -> bool:
        """Deactivates a device token by setting its active status to False."""
        token_clean = device_token.strip()
        devices = self._load_devices()
        if token_clean in devices:
            devices[token_clean]["activo"] = False
            self._save_devices(devices)
            logger.info(f"Deactivated push device: ...{token_clean[-8:]}")
            return True
        return False

    def listar_dispositivos(self, solo_activos: bool = True) -> List[Dict[str, Any]]:
        """Returns all registered devices, optionally filtering only active ones."""
        devices = self._load_devices()
        items = list(devices.values())
        if solo_activos:
            return [d for d in items if d.get("activo", True)]
        return items

    def contar_dispositivos(self, solo_activos: bool = True) -> int:
        """Returns the number of registered devices."""
        return len(self.listar_dispositivos(solo_activos=solo_activos))

    def limpiar_dispositivos(self) -> None:
        """Clears all devices from memory and disk (primarily for test fixtures)."""
        self._save_devices({})
        self.sent_notifications.clear()

    def send_message(
        self,
        recipient_id: str,
        message: str,
        parse_mode: Optional[str] = None,
        raise_on_error: bool = True,
        **kwargs: Any,
    ) -> bool:
        """Sends a push notification to a specific token or to all registered devices.

        Args:
            recipient_id: Device token, 'broadcast', 'all', or alias.
            message: Body text of the notification.
            parse_mode: Formatting mode (ignored or passed as metadata).
            raise_on_error: If True, re-raises network or API exceptions.
            **kwargs: Extra parameters like 'title', 'extra_data'.

        Returns:
            bool: True if sent or simulated successfully, False otherwise.
        """
        title = str(kwargs.get("title") or "Gamma Finanzas")
        extra_data = dict(kwargs.get("extra_data") or {})

        rec_clean = recipient_id.strip()
        is_broadcast = rec_clean.lower() in ("broadcast", "all", "*")

        target_tokens: List[str] = []
        if is_broadcast:
            devices = self.listar_dispositivos(solo_activos=True)
            target_tokens = [d["device_token"] for d in devices]
            if not target_tokens:
                logger.warning(
                    "Broadcast push requested but no active devices are registered. Simulating delivery."
                )
                target_tokens = ["simulated-broadcast"]
        else:
            target_tokens = [rec_clean]

        for token in target_tokens:
            try:
                if self.http_client is not None:
                    # Invocación cliente HTTP inyectado
                    self.http_client.post(
                        "https://fcm.googleapis.com/fcm/send",
                        json={
                            "to": token,
                            "notification": {"title": title, "body": message},
                            "data": extra_data,
                        },
                    )
                record = SentPushRecord(
                    recipient_id=token,
                    message=message,
                    parse_mode=parse_mode,
                    title=title,
                    extra_data=extra_data,
                    timestamp=time.time(),
                )
                self.sent_notifications.append(record)
                token_preview = token[-8:] if len(token) >= 8 else token
                logger.info(
                    f"Push notification dispatched to ...{token_preview}: "
                    f"{title} - {message[:40]}"
                )
            except Exception as exc:
                logger.error(f"Error dispatching push notification: {exc}")
                if raise_on_error:
                    raise exc
                return False

        return True

    def send_document(
        self,
        recipient_id: str,
        document_path: str,
        caption: str = "",
        visible_file_name: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Sends a document payload as a push notification."""
        file_label = visible_file_name or Path(document_path).name
        body = caption or f"Nuevo archivo disponible: {file_label}"
        data = dict(kwargs.get("extra_data") or {})
        data["document_path"] = str(document_path)
        data["filename"] = file_label

        return self.send_message(
            recipient_id=recipient_id,
            message=body,
            title=str(kwargs.get("title") or "Documento Gamma"),
            extra_data=data,
            **kwargs,
        )
