class DriveService:
    @staticmethod
    def upload_backup(file_path: str) -> str:
        # Mock implementation
        return f"mock_drive_id_for_{file_path.split('/')[-1]}"
