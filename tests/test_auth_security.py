import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestAuthSecurity(unittest.TestCase):
    """Verify fail-closed behavior: missing secrets always yield 403."""

    def _make_app(self, env_overrides: dict):
        """Create a fresh Flask test client with specific env vars."""
        for k, v in env_overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

        # Ensure required vars for bot init
        os.environ.setdefault("TOKEN", "test_token_123")
        os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")

        with patch("com.bot.GAMMA") as MockGamma, patch(
            "logic.cron_jobs.notificacion_clima"
        ), patch("logic.cron_jobs.resumen_semanal"), patch(
            "logic.cron_jobs.rotar_logs"
        ):
            mock_instance = MockGamma.return_value
            mock_instance.bot = MagicMock()
            mock_instance.token = "test_token_123"

            # Force re-import to pick up new env
            import importlib
            import config as config_mod

            importlib.reload(config_mod)

            import flask_app as fa_mod

            importlib.reload(fa_mod)
            fa_mod.app.config["TESTING"] = True
            return fa_mod.app.test_client()

    def test_deploy_403_without_webhook_secret(self):
        """POST /deploy without GITHUB_WEBHOOK_SECRET must return 403."""
        client = self._make_app(
            {
                "GITHUB_WEBHOOK_SECRET": None,
                "FLASK_ENV": "development",
            }
        )
        resp = client.post("/deploy", data=b"{}")
        self.assertEqual(resp.status_code, 403)

    def test_deploy_403_without_webhook_secret_production(self):
        """POST /deploy without GITHUB_WEBHOOK_SECRET in production must return 403 or fail to start."""
        with self.assertRaises(RuntimeError) as context:
            self._make_app(
                {
                    "GITHUB_WEBHOOK_SECRET": None,
                    "FLASK_ENV": "production",
                }
            )
        self.assertIn(
            "Variables de entorno requeridas en producci", str(context.exception)
        )

    def test_cron_403_without_cron_secret(self):
        """GET /cron/clima without CRON_SECRET must return 403."""
        client = self._make_app(
            {
                "CRON_SECRET": None,
                "FLASK_ENV": "development",
            }
        )
        resp = client.get("/cron/clima")
        self.assertEqual(resp.status_code, 403)

    def test_cron_403_with_secret_in_query_string(self):
        """GET /cron/clima?secret=correct must still return 403 — only header accepted."""
        client = self._make_app(
            {
                "CRON_SECRET": "my_secret",
                "FLASK_ENV": "development",
            }
        )
        resp = client.get("/cron/clima?secret=my_secret")
        self.assertEqual(resp.status_code, 403)

    def test_cron_200_with_header_secret(self):
        """GET /cron/clima with correct X-Cron-Secret header should not return 403."""
        client = self._make_app(
            {
                "CRON_SECRET": "my_secret",
                "FLASK_ENV": "development",
                "CHAT_ID": "12345",
            }
        )
        with patch("flask_app.notificacion_clima", return_value=True):
            resp = client.get("/cron/clima", headers={"X-Cron-Secret": "my_secret"})
        self.assertNotEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
