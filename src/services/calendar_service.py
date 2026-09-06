class CalendarService:
    @staticmethod
    def create_event(title: str, date: str, description: str) -> str:
        # Mock implementation
        return f"mock_event_id_{title.replace(' ', '_')}"

    @staticmethod
    def mark_event_completed(event_id: str) -> bool:
        # Mock implementation
        return True
