#!/usr/bin/env python3
"""
PDFファイルを各ページごとの画像に変換するスクリプト
"""
from pathlib import Path
import fitz  # PyMuPDF
from config import DATA_DIR, RESULTS_IMAGES_DIR
from logging_utils import get_app_logger


def pdf_to_images(pdf_path: Path, output_dir: Path = RESULTS_IMAGES_DIR, image_format: str = "jpg"):
    """
    PDFファイルを各ページごとの画像に変換

    Args:
        pdf_path: PDFファイルのパス
        output_dir: 出力ディレクトリ (デフォルト: results/images)
        image_format: 画像フォーマット (jpeg, png, gif など)
    """
    logger = get_app_logger()

    # 出力ディレクトリを作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # PDFを開く
    logger.info("Converting %s to images", pdf_path)
    pdf_document = fitz.open(pdf_path)

    # 各ページを画像として保存
    total_pages = len(pdf_document)
    for page_num in range(total_pages):
        page = pdf_document[page_num]
        # 300 DPIに相当する倍率 (72 DPI * 4.166 ≈ 300 DPI)
        mat = fitz.Matrix(4.166, 4.166)
        pix = page.get_pixmap(matrix=mat)

        output_file = output_dir / f"page_{page_num + 1}.{image_format}"
        pix.save(str(output_file))
        logger.info("Saved image: %s", output_file)

    pdf_document.close()
    logger.info("Conversion completed. Total pages: %s", total_pages)


def main():
    # dataディレクトリ内のPDFファイルを検索
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        get_app_logger().error("No PDF files found in data directory")
        return

    if len(pdf_files) > 1:
        get_app_logger().warning("Multiple PDF files found. Processing the first one.")

    pdf_file = pdf_files[0]
    get_app_logger().info("Processing: %s", pdf_file)

    # PDFを画像に変換
    pdf_to_images(pdf_file, output_dir=RESULTS_IMAGES_DIR, image_format="jpg")


if __name__ == "__main__":
    main()
