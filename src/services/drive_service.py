"""Servicio de integración con Google Drive para almacenamiento de backups contables.

Implementa subida automática a Google Drive v3 con fallback determinista a
almacenamiento local seguro cuando la API no está configurada o falla.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Any, Optional

from logger_config import setup_logger

logger = setup_logger("drive_service")

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "data" / "backups"


class DriveService:
    """Gestor de subida de backups a Google Drive con contingencia local."""

    _service: Any = None

    @classmethod
    def _get_drive_client(cls) -> Any:
        """Inicializa y cachea el cliente de Google Drive si las credenciales existen."""
        if cls._service is not None:
            return cls._service

        candidate_paths = [
            BASE_DIR / "credentials.json",
            BASE_DIR.parent / "credentials.json",
            Path.cwd() / "src" / "credentials.json",
            Path.cwd() / "credentials.json",
        ]
        cred_path: Optional[Path] = None
        for p in candidate_paths:
            if p.exists():
                cred_path = p
                break

        if not cred_path:
            logger.info(
                "credentials.json no encontrado; se utilizará fallback local para backups."
            )
            return None

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            scopes = [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(str(cred_path), scopes=scopes)
            cls._service = build("drive", "v3", credentials=creds)
            return cls._service
        except Exception as e:
            logger.warning(f"No se pudo inicializar Google Drive API: {e}")
            return None

    @classmethod
    def upload_backup(cls, file_path: str, folder_id: Optional[str] = None) -> str:
        """Sube un archivo de backup a Google Drive con fallback seguro a almacenamiento local."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            logger.error(f"El archivo de backup no existe o no es válido: {file_path}")
            return ""

        # 1. Intentar subida a Google Drive
        drive_client = cls._get_drive_client()
        if drive_client:
            try:
                from googleapiclient.http import MediaFileUpload

                file_metadata: dict[str, Any] = {"name": p.name}
                if folder_id:
                    file_metadata["parents"] = [folder_id]

                media = MediaFileUpload(str(p), mimetype="text/csv", resumable=True)
                try:
                    uploaded = (
                        drive_client.files()
                        .create(body=file_metadata, media_body=media, fields="id")
                        .execute()
                    )
                    drive_id = str(uploaded.get("id", ""))
                    if drive_id:
                        logger.info(
                            f"Backup subido exitosamente a Google Drive con ID: {drive_id}"
                        )
                        return drive_id
                finally:
                    if hasattr(media, "_fd") and media._fd:
                        try:
                            if hasattr(media._fd, "close"):
                                media._fd.close()
                            else:
                                os.close(media._fd)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(
                    f"Fallo durante la subida a Google Drive ({e}). Procediendo con fallback local."
                )

        # 2. Fallback determinista local
        try:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            target = BACKUP_DIR / p.name
            shutil.copy2(p, target)
            local_id = f"local:{p.name}"
            logger.info(f"Backup persistido localmente con éxito en: {target}")
            return local_id
        except Exception as err:
            logger.error(f"Error crítico guardando backup local en {BACKUP_DIR}: {err}")
            return ""
