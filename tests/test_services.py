import unittest
from services.calendar_service import CalendarService
from services.drive_service import DriveService

class TestServices(unittest.TestCase):
    def test_calendar_create_event(self):
        result = CalendarService.create_event("Test", "2026-09-04", "Desc")
        self.assertEqual(result, "mock_event_id_Test")

    def test_calendar_mark_completed(self):
        result = CalendarService.mark_event_completed("mock_id")
        self.assertTrue(result)

    def test_drive_upload_backup(self):
        result = DriveService.upload_backup("/path/to/file.csv")
        self.assertEqual(result, "mock_drive_id_for_file.csv")

if __name__ == '__main__':
    unittest.main()
