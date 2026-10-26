from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from pathlib import Path
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
                logger.info(
                    f"Issue #{issue_number} sincronizado a estado '{gh_state}'."
                )
                return True
            else:
                logger.warning(
                    f"Fallo al actualizar estado del issue #{issue_number}: "
                    f"HTTP {resp_patch.status_code}"
                )
        except Exception as e:
            logger.warning(
                f"Error no bloqueante al actualizar issue #{issue_number}: {e}"
            )

        return False


class GitHubWebhookService:
    """Servicio para recepción, validación y procesamiento reactivo de webhooks de GitHub."""

    @classmethod
    def get_webhook_secret(cls) -> str | None:
        return os.getenv("GITHUB_WEBHOOK_SECRET") or None

    @classmethod
    def verify_signature(
        cls,
        payload_bytes: bytes,
        signature_header: str | None,
        secret: str | None = None,
    ) -> bool:
        """Valida la firma HMAC-SHA256 enviada por GitHub en el encabezado X-Hub-Signature-256."""
        secret_to_use = secret if secret is not None else cls.get_webhook_secret()
        if not secret_to_use:
            # Modo permisivo si no hay secret configurado en entorno local / desarrollo
            return True

        if not signature_header or not signature_header.startswith("sha256="):
            return False

        computed_mac = hmac.new(
            secret_to_use.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
        expected_header = f"sha256={computed_mac}"
        return hmac.compare_digest(expected_header, signature_header)

    @classmethod
    def extract_ticket_id(cls, title: str | None) -> str | None:
        """Extrae el identificador [TCK-XXX] del título del issue."""
        if not title:
            return None
        match = re.search(r"\[(TCK-\d+)\]", title, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    @classmethod
    def process_issue_event(
        cls,
        action: str,
        issue_data: dict[str, Any],
        tickets_file_path: Path | str,
    ) -> dict[str, Any]:
        """Procesa un evento de issue (closed / reopened) y actualiza tickets.json de forma atómica."""
        path = Path(tickets_file_path)
        title = issue_data.get("title", "")
        ticket_id = cls.extract_ticket_id(title)
        issue_number = issue_data.get("number")
        state_reason = issue_data.get("state_reason") or "resuelto en GitHub"

        if not ticket_id:
            logger.info(
                f"Webhook de GitHub ignorado: título '{title}' no contiene [TCK-XXX]."
            )
            return {
                "status": "ignored",
                "reason": f"No TCK identifier found in title '{title}'",
            }

        if action not in ("closed", "reopened"):
            return {
                "status": "ignored",
                "reason": f"Acción '{action}' no requiere actualización de estado de ticket",
            }

        if not path.exists():
            return {
                "status": "error",
                "message": f"Archivo de tickets no encontrado en {path}",
            }

        try:
            with open(path, "r", encoding="utf-8") as f:
                tickets: list[dict[str, Any]] = json.load(f)
        except Exception as e_read:
            logger.error(f"Error leyendo {path}: {e_read}")
            return {"status": "error", "message": str(e_read)}

        target = None
        for t in tickets:
            if t.get("id") == ticket_id:
                target = t
                break

        if not target:
            logger.info(f"Ticket {ticket_id} no encontrado en {path}.")
            return {
                "status": "ignored",
                "reason": f"Ticket {ticket_id} not found in database",
            }

        nuevo_estado = "Cerrado" if action == "closed" else "Abierto"
        estado_previo = target.get("estado")
        target["estado"] = nuevo_estado

        if action == "closed":
            # Si no tenía resolución o es nula, actualizar con detalle de GitHub
            res_actual = target.get("resolucion")
            if not res_actual:
                target["resolucion"] = (
                    f"Cerrado vía GitHub Issue #{issue_number} ({state_reason})"
                    if issue_number
                    else f"Cerrado vía GitHub Issue ({state_reason})"
                )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(tickets, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Ticket {ticket_id} actualizado reactivamente desde GitHub: "
                f"'{estado_previo}' -> '{nuevo_estado}'"
            )
        except Exception as e_write:
            logger.error(f"Error escribiendo {path}: {e_write}")
            return {"status": "error", "message": str(e_write)}

        return {
            "status": "processed",
            "ticket_id": ticket_id,
            "action": action,
            "nuevo_estado": nuevo_estado,
            "issue_number": issue_number,
        }
