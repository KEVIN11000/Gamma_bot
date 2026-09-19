from logger_config import setup_logger

logger = setup_logger("calendar_service")


class CalendarService:
    @staticmethod
    def create_event(title: str, date: str, description: str) -> str:
        """Placeholder — Calendar integration not yet implemented."""
        logger.warning("CalendarService.create_event no implementado")
        return ""

    @staticmethod
    def mark_event_completed(event_id: str) -> bool:
        """Placeholder — Calendar integration not yet implemented."""
        if not event_id:
            return False
        logger.warning("CalendarService.mark_event_completed no implementado")
        return False
