#!/usr/bin/env python3
"""
ロギング設定
"""
import logging
from pathlib import Path

from config import RESULTS_LOGS_DIR, RESULTS_PAGE_LOGS_DIR


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _configure_logger(logger: logging.Logger, log_file: Path) -> logging.Logger:
    if logger.handlers:
        return logger

    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_app_logger() -> logging.Logger:
    return _configure_logger(logging.getLogger("ocr.app"), RESULTS_LOGS_DIR / "app.log")


def get_page_logger(page_number: int) -> logging.Logger:
    log_file = RESULTS_PAGE_LOGS_DIR / f"page_{page_number}.log"
    return _configure_logger(logging.getLogger(f"ocr.page.{page_number}"), log_file)
