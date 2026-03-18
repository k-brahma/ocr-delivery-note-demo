#!/usr/bin/env python3
"""
プロジェクト内で共通利用する設定
"""
import os
from pathlib import Path


DATA_DIR = Path("data")
RESULTS_DIR = Path("results")
RESULTS_IMAGES_DIR = RESULTS_DIR / "images"
RESULTS_JSON_DIR = RESULTS_DIR / "json"
RESULTS_SUMMARY_DIR = RESULTS_DIR / "summary"
RESULTS_LOGS_DIR = RESULTS_DIR / "logs"
RESULTS_PAGE_LOGS_DIR = RESULTS_LOGS_DIR / "pages"
OCR_MAX_WORKERS = os.cpu_count() or 1


def ocr_worker_count(task_count: int) -> int:
    """
    OCR処理に使うスレッド数を返す
    """
    return max(1, min(OCR_MAX_WORKERS, task_count))


def page_image_path(page_number: int, image_suffix: str = ".jpg") -> Path:
    """
    OCR対象となるページ画像のパスを返す
    """
    return RESULTS_IMAGES_DIR / f"page_{page_number}{image_suffix}"
