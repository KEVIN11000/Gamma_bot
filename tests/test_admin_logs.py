"""Tests unitarios para el endpoint seguro /admin/logs en Flask."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestAdminLogs(unittest.TestCase):
    """Verifica autenticación y entrega de logs en /admin/logs."""

    def _make_app(self, cron_secret: str = "test_cron_secret_123"):
        os.environ["CRON_SECRET"] = cron_secret
        os.environ.setdefault("TOKEN", "test_token_123")
        os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")
        os.environ["FLASK_ENV"] = "development"

        with patch("com.bot.GAMMA") as MockGamma, patch(
            "logic.cron_jobs.notificacion_clima"
        ), patch("logic.cron_jobs.resumen_semanal"), patch(
            "logic.cron_jobs.rotar_logs"
        ):
            mock_instance = MockGamma.return_value
            mock_instance.bot = MagicMock()
            mock_instance.token = "test_token_123"

            import importlib
            import config as config_mod

            importlib.reload(config_mod)

            import flask_app as fa_mod

            importlib.reload(fa_mod)
            fa_mod.app.config["TESTING"] = True
            return fa_mod.app.test_client()

    def test_admin_logs_403_without_secret(self) -> None:
        client = self._make_app()
        resp = client.get("/admin/logs")
        self.assertEqual(resp.status_code, 403)

    def test_admin_logs_403_with_wrong_secret(self) -> None:
        client = self._make_app()
        resp = client.get(
            "/admin/logs", headers={"X-Cron-Secret": "secreto_equivocado"}
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_logs_200_with_valid_secret(self) -> None:
        client = self._make_app("clave_secreta_vigia")
        resp = client.get(
            "/admin/logs", headers={"X-Cron-Secret": "clave_secreta_vigia"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("lines", data)
        self.assertIn("server_time", data)
        self.assertIn("total_lines", data)

    def test_admin_logs_respects_lines_param(self) -> None:
        client = self._make_app("clave_secreta_vigia")
        resp = client.get(
            "/admin/logs?lines=3",
            headers={"X-Cron-Secret": "clave_secreta_vigia"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertLessEqual(data["returned_lines"], 3)


if __name__ == "__main__":
    unittest.main()
