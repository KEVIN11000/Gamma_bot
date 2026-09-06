from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz
import os

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "gen_log.txt"
tz_py = pytz.timezone("America/Buenos_Aires")


class TimezoneFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz_py)
        return dt.timetuple()

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz_py)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


def setup_logger(name="gamma_bot") -> Any:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = TimezoneFormatter("[%(asctime)s] %(message)s")

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        # Restrict log file permissions to owner only
        try:
            os.chmod(LOG_FILE, 0o600)
        except Exception:
            pass

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger
