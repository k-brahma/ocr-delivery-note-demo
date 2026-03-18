#!/usr/bin/env python3
"""
PDFごとのOCRページ設定をCSVから読み込む
"""
import csv
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from config import DATA_DIR


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off", ""}


@dataclass(frozen=True)
class PageConfig:
    page: int
    is_multiple: bool
    rotate_clockwise: bool = False


def _parse_bool(value: str, field_name: str, config_path: Path, row_number: int) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(
        f"{config_path} row {row_number}: invalid {field_name} value '{value}'"
    )


def pages_config_path(pdf_path: Path) -> Path:
    return DATA_DIR / f"{pdf_path.stem}.csv"


def load_pages_config(pdf_path: Path) -> list[PageConfig]:
    config_path = pages_config_path(pdf_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Page config CSV not found: {config_path}. "
            "Create data/<pdf_stem>.csv with columns: page,is_multiple,rotate_clockwise"
        )

    with config_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required_columns = {"page", "is_multiple"}
        if reader.fieldnames is None:
            raise ValueError(f"{config_path} is empty")

        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{config_path} is missing required columns: {missing}")

        pages_config = []
        for row_number, row in enumerate(reader, start=2):
            page_value = (row.get("page") or "").strip()
            if not page_value:
                raise ValueError(f"{config_path} row {row_number}: page is required")

            try:
                page = int(page_value)
            except ValueError as exc:
                raise ValueError(
                    f"{config_path} row {row_number}: page must be an integer"
                ) from exc

            is_multiple = _parse_bool(
                row.get("is_multiple", ""),
                "is_multiple",
                config_path,
                row_number,
            )
            rotate_clockwise = _parse_bool(
                row.get("rotate_clockwise", ""),
                "rotate_clockwise",
                config_path,
                row_number,
            )
            pages_config.append(
                PageConfig(
                    page=page,
                    is_multiple=is_multiple,
                    rotate_clockwise=rotate_clockwise,
                )
            )

    if not pages_config:
        raise ValueError(f"{config_path} does not contain any page config rows")

    return pages_config


def save_pages_config(pdf_path: Path, pages_config: list[PageConfig]) -> Path:
    config_path = pages_config_path(pdf_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with config_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["page", "is_multiple", "rotate_clockwise"],
        )
        writer.writeheader()
        for page_config in pages_config:
            writer.writerow(
                {
                    "page": page_config.page,
                    "is_multiple": str(page_config.is_multiple).lower(),
                    "rotate_clockwise": str(page_config.rotate_clockwise).lower(),
                }
            )

    return config_path


def default_pages_config(pdf_path: Path) -> list[PageConfig]:
    with fitz.open(pdf_path) as document:
        total_pages = len(document)

    return [
        PageConfig(page=page_number, is_multiple=False, rotate_clockwise=False)
        for page_number in range(1, total_pages + 1)
    ]
