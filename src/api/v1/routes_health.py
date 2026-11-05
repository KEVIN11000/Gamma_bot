from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify

from api.security import require_api_key

health_bp = Blueprint("health_v1", __name__)


def _get_version() -> str:
    version_path = Path(__file__).resolve().parent.parent.parent.parent / "VERSION"
    if version_path.exists():
        return version_path.read_text(encoding="utf-8").strip()
    return "2.1.0"


@health_bp.route("/health", methods=["GET"])
@require_api_key
def health_check() -> Any:
    current_version = _get_version()
    return (
        jsonify(
            {
                "status": "ok",
                "sheets": True,
                "sheets_connected": True,
                "calendar_connected": True,
                "avisos": True,
                "version": current_version,
                "version_api": current_version,
                "mobile_version": "0.0.10",
                "latest_app_version": "0.0.10",
                "latest_app_version_code": 62,
                "download_url": (
                    "https://github.com/KEVIN11000/Gamma_Mobile/releases/latest"
                ),
                "apk_download_url": (
                    "https://github.com/KEVIN11000/Gamma_Mobile/releases/"
                    "download/v0.0.10/gamma-mobile-v0.0.10-release.apk"
                ),
            }
        ),
        200,
    )
