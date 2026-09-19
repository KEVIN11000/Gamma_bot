from logger_config import setup_logger

logger = setup_logger("drive_service")


class DriveService:
    @staticmethod
    def upload_backup(file_path: str) -> str:
        """Placeholder — Drive backup not yet implemented."""
        logger.warning(
            "DriveService.upload_backup no implementado — backup local únicamente"
        )
        return ""
