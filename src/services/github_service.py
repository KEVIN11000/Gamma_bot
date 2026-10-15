from __future__ import annotations

import logging
import os
from typing import Any
import requests

logger = logging.getLogger("github_sync")


class GitHubIssueSyncService:
    """Servicio de sincronización bidireccional entre tickets locales y GitHub Issues."""

    DEFAULT_REPO = "KEVIN11000/Gamma_Mobile"

    @classmethod
    def get_token(cls) -> str | None:
        return os.getenv("GITHUB_TOKEN") or None

    @classmethod
    def get_repo(cls) -> str:
        return os.getenv("GITHUB_REPO") or cls.DEFAULT_REPO

    @classmethod
    def is_configured(cls) -> bool:
        return cls.get_token() is not None

    @classmethod
    def _headers(cls) -> dict[str, str]:
        token = cls.get_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Gamma-Bot-Ticket-Sync",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @classmethod
    def create_github_issue(cls, ticket: dict[str, Any]) -> int | None:
        """Crea un issue en GitHub a partir de un ticket nuevo si GITHUB_TOKEN está presente."""
        if not cls.is_configured():
            return None

        repo = cls.get_repo()
        url = f"https://api.github.com/repos/{repo}/issues"
        ticket_id = ticket.get("id", "TCK")
        asunto = ticket.get("asunto", "Sin Asunto")
        origen = ticket.get("origen", "app")
        fecha = ticket.get("fecha", "")
        descripcion = ticket.get("descripcion", "")

        payload = {
            "title": f"[{ticket_id}] {asunto}",
            "body": (
                f"### 🎫 Reporte de Soporte: `{ticket_id}`\n\n"
                f"- **Origen:** `{origen}`\n"
                f"- **Fecha:** `{fecha}`\n\n"
                f"#### Descripción:\n{descripcion}\n"
            ),
            "labels": ["soporte", f"origen:{origen}"],
        }

        try:
            resp = requests.post(url, json=payload, headers=cls._headers(), timeout=5)
            if resp.status_code == 201:
                data = resp.json()
                issue_number = data.get("number")
                logger.info(f"Issue #{issue_number} creado en GitHub para {ticket_id}.")
                return issue_number
            else:
                logger.warning(
                    f"Fallo al crear issue en GitHub para {ticket_id}: "
                    f"HTTP {resp.status_code} - {resp.text}"
                )
        except Exception as e:
            logger.warning(f"Error no bloqueante al comunicar con GitHub Issues: {e}")
        return None

    @classmethod
    def sync_ticket_status(
        cls,
        ticket_id: str,
        nuevo_estado: str,
        resolucion: str | None = None,
        issue_number: int | None = None,
    ) -> bool:
        """Sincroniza el cambio de estado (Abierto / Cerrado) hacia GitHub Issues."""
        if not cls.is_configured():
            return False

        repo = cls.get_repo()

        # Si no tenemos número de issue, intentar buscarlo por el título
        if not issue_number:
            try:
                search_url = f"https://api.github.com/repos/{repo}/issues"
                params = {"state": "all", "per_page": 50}
                resp = requests.get(
                    search_url, headers=cls._headers(), params=params, timeout=5
                )
                if resp.status_code == 200:
                    for issue in resp.json():
                        title = issue.get("title", "")
                        if f"[{ticket_id}]" in title:
                            issue_number = issue.get("number")
                            break
            except Exception as e_search:
                logger.warning(f"Error buscando issue para {ticket_id}: {e_search}")

        if not issue_number:
            logger.info(f"No se encontró issue en GitHub para {ticket_id}.")
            return False

        # Mapear estado
        gh_state = "closed" if nuevo_estado == "Cerrado" else "open"
        patch_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
        payload: dict[str, Any] = {"state": gh_state}

        try:
            # Si hay resolución y se cierra, agregar comentario opcional
            if resolucion and nuevo_estado == "Cerrado":
                comment_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
                comment_payload = {
                    "body": f"✅ **Ticket resuelto desde Gamma:**\n{resolucion}"
                }
                requests.post(
                    comment_url,
                    json=comment_payload,
                    headers=cls._headers(),
                    timeout=5,
                )

            resp_patch = requests.patch(
                patch_url, json=payload, headers=cls._headers(), timeout=5
            )
            if resp_patch.status_code == 200:
                logger.info(f"Issue #{issue_number} sincronizado a estado '{gh_state}'.")
                return True
            else:
                logger.warning(
                    f"Fallo al actualizar estado del issue #{issue_number}: "
                    f"HTTP {resp_patch.status_code}"
                )
        except Exception as e:
            logger.warning(f"Error no bloqueante al actualizar issue #{issue_number}: {e}")

        return False
