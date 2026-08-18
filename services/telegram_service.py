from __future__ import annotations

from typing import Any


class TelegramService:
    def __init__(self, repository: Any) -> None:
        """Initialize with a repository instance.

        Parameters
        ----------
        repository: Any
            An instance of ``repositories.sheets_repository.SheetsRepository``
            (or a mock in tests). The service stores it for potential future use
            inside handler code.
        """
        self.repository = repository

    def register_handlers(self, bot: Any, gamma_app: Any) -> None:
        """Register all Telegram command handlers.

        This method imports the original handler registration functions from the
        ``com.handlers`` package and forwards the ``bot`` and ``gamma_app``
        objects. Handlers may later retrieve ``self.repository`` if needed.
        """
        from com.handlers.asistencia import register_asistencia_handlers
        from com.handlers.avisos import register_avisos_handlers
        from com.handlers.base import register_base_handlers
        from com.handlers.finanzas import register_finanzas_handlers

        register_base_handlers(bot, gamma_app)
        register_asistencia_handlers(bot, gamma_app)
        register_finanzas_handlers(bot, gamma_app)
        register_avisos_handlers(bot, gamma_app)
