from __future__ import annotations

import functools
import hashlib
import hmac
import os
from typing import Callable, Any
from flask import request, jsonify
from flask_limiter import Limiter


def get_client_ip() -> str:
    """Extrae la IP real del cliente considerando cabeceras de proxy inverso."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


# Instancia central de Limiter para toda la aplicación
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["10 per minute"],
    storage_uri="memory://",
)


def is_valid_api_key(provided_key: str | None) -> bool:
    if not provided_key:
        return False
    expected_key = (
        os.getenv("X_API_KEY") or os.getenv("GAMMA_MOBILE_API_KEY") or "dev-key"
    )
    # Timing-attack resistant hash comparison
    h_provided = hashlib.sha256(provided_key.encode("utf-8")).digest()
    h_expected = hashlib.sha256(expected_key.encode("utf-8")).digest()
    return hmac.compare_digest(h_provided, h_expected)


def is_valid_webhook_secret(provided_secret: str | None) -> bool:
    if not provided_secret:
        return False
    expected_secret = (
        os.getenv("WHATSAPP_WEBHOOK_SECRET")
        or os.getenv("WEBHOOK_SECRET")
        or os.getenv("X_API_KEY")
        or "dev-webhook-secret"
    )
    h_provided = hashlib.sha256(provided_secret.encode("utf-8")).digest()
    h_expected = hashlib.sha256(expected_secret.encode("utf-8")).digest()
    return hmac.compare_digest(h_provided, h_expected)


def require_api_key(f: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        api_key = request.headers.get("X-API-KEY")
        if not is_valid_api_key(api_key):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "X-API-KEY inválida o no proporcionada",
                        }
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated_function


def require_webhook_secret(f: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        secret = request.headers.get("X-Webhook-Secret") or request.headers.get(
            "X-API-KEY"
        )
        if not is_valid_webhook_secret(secret):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "X-Webhook-Secret inválido o no proporcionado",
                        }
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated_function
