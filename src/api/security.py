from __future__ import annotations

import functools
import hashlib
import hmac
import os
from typing import Callable, Any
from flask import request, jsonify


def is_valid_api_key(provided_key: str | None) -> bool:
    if not provided_key:
        return False
    expected_key = os.getenv("X_API_KEY", "dev-key")
    # Timing-attack resistant hash comparison
    h_provided = hashlib.sha256(provided_key.encode("utf-8")).digest()
    h_expected = hashlib.sha256(expected_key.encode("utf-8")).digest()
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
