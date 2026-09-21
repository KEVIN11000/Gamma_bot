"""Módulo de Telemetría e Incidentes Vigía para Gamma_bot.

Permite reportar errores críticos del servidor (Flask, Cron, Worker) directamente
hacia GitHub Issues de forma fail-safe, sanitizando credenciales y aplicando
cooldown para evitar spam de issues repetidos.
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

DEFAULT_REPO = "KEVIN11000/Gamma_bot"
COOLDOWN_SECONDS = 1800  # 30 minutos por firma de error
_COOLDOWN_REGISTRY: Dict[str, float] = {}

# Claves sensibles a enmascarar en logs y stack traces
SENSIBLE_ENV_KEYS = [
    "TOKEN",
    "CHAT_ID",
    "SPREADSHEET_ID",
    "GEMINI_API_KEY",
    "FLASK_SECRET_KEY",
    "GITHUB_WEBHOOK_SECRET",
    "CRON_SECRET",
    "CALENDAR_ID",
    "LIBRO_CONTABLE_ID",
    "PANEL_CLAVE",
    "GITHUB_TOKEN",
    "GH_TOKEN",
]


def sanitizar_texto(texto: str) -> str:
    """Reemplaza valores de variables sensibles por [REDACTED]."""
    if not texto:
        return ""
    sanitizado = texto
    for key in SENSIBLE_ENV_KEYS:
        val = os.getenv(key)
        if val and len(val.strip()) > 3:
            sanitizado = sanitizado.replace(val.strip(), f"[{key}_REDACTED]")
    return sanitizado


def reportar_incidente_vigia(
    titulo: str,
    detalle: str,
    origen: str = "servidor",
    traceback_str: Optional[str] = None,
    repo: str = DEFAULT_REPO,
    token: Optional[str] = None,
) -> bool:
    """Envía un reporte de error crítico como GitHub Issue de forma fail-safe.

    Retorna True si el issue fue creado exitosamente en GitHub, False de lo contrario.
    Nunca propaga excepciones.
    """
    global _COOLDOWN_REGISTRY

    # 1. Deduplicación por cooldown (anti-spam)
    firma = f"{origen}:{titulo}"
    firma_hash = hashlib.sha256(firma.encode("utf-8")).hexdigest()
    ahora = time.time()
    ultimo_envio = _COOLDOWN_REGISTRY.get(firma_hash, 0)
    if ahora - ultimo_envio < COOLDOWN_SECONDS:
        return False

    # 2. Token de GitHub
    gh_token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not gh_token or not requests:
        return False

    # 3. Sanitizar detalle y traceback
    safe_titulo = sanitizar_texto(titulo)[:120]
    safe_detalle = sanitizar_texto(detalle)
    safe_tb = sanitizar_texto(traceback_str or "")

    timestamp = datetime.now(timezone.utc).isoformat()
    issue_title = f"[Vigía {origen.capitalize()}] {safe_titulo}"

    body_lines = [
        "### 🚨 Incidente Crítico Detectado por Vigía",
        f"- **Origen:** `{origen}`",
        f"- **Fecha (UTC):** `{timestamp}`",
        "\n#### Detalle:",
        safe_detalle,
    ]
    if safe_tb:
        body_lines.append(f"\n#### Stacktrace:\n```text\n{safe_tb}\n```")

    payload: Dict[str, Any] = {
        "title": issue_title,
        "body": "\n".join(body_lines),
        "labels": ["vigia", "server-error", "bug"],
    }

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {gh_token}",
        "User-Agent": "GammaBot-Vigia/1.0",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        if resp.status_code == 201:
            _COOLDOWN_REGISTRY[firma_hash] = ahora
            return True
        return False
    except Exception:
        return False
