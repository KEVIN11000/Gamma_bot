import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestRateLimiting(unittest.TestCase):
    """Verify that rate limiting is actually enforced on protected endpoints."""

    def setUp(self):
        # Set required env vars for app initialization
        os.environ.setdefault("TOKEN", "test_token_123")
        os.environ.setdefault("SPREADSHEET_ID", "test_sheet_id")
        os.environ.setdefault("FLASK_ENV", "development")
        os.environ.setdefault("CRON_SECRET", "test_cron_secret")
        os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test_webhook_secret")

        # Mock bot and sheets before importing flask_app
        with patch("com.bot.GAMMA") as MockGamma, patch(
            "logic.cron_jobs.notificacion_clima"
        ), patch("logic.cron_jobs.resumen_semanal"), patch(
            "logic.cron_jobs.rotar_logs"
        ):
            mock_instance = MockGamma.return_value
            mock_instance.bot = MagicMock()
            mock_instance.token = "test_token_123"

            from flask_app import app, limiter

            self.app = app
            self.limiter = limiter

        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_deploy_rate_limit_enforced(self):
        """POST /deploy should return 429 after exceeding the rate limit."""
        # The limit is 10/min; send 12 requests
        responses = []
        for _ in range(12):
            resp = self.client.post("/deploy", data=b"{}")
            responses.append(resp.status_code)
        self.assertIn(429, responses, "Rate limit was not enforced on /deploy")

    def test_cron_rate_limit_enforced(self):
        """GET /cron/clima should return 429 after exceeding the rate limit."""
        responses = []
        for _ in range(12):
            resp = self.client.get(
                "/cron/clima", headers={"X-Cron-Secret": "test_cron_secret"}
            )
            responses.append(resp.status_code)
        self.assertIn(429, responses, "Rate limit was not enforced on /cron/clima")


if __name__ == "__main__":
    unittest.main()
