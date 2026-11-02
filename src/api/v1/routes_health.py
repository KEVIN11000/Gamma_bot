from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify

from api.security import require_api_key

health_bp = Blueprint("health_v1", __name__)


@health_bp.route("/health", methods=["GET"])
@require_api_key
def health_check() -> Any:
    return (
        jsonify(
            {
                "status": "ok",
                "sheets": True,
                "sheets_connected": True,
                "calendar_connected": True,
                "avisos": True,
                "version": "2.0.0",
                "version_api": "2.0.0",
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
