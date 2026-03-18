#!/usr/bin/env python3
"""
PDFから納品書データを抽出してExcel/CSVを生成するメインスクリプト

処理フロー:
1. PDFをJPEG画像に変換
2. 必要に応じて画像を回転
3. 各ページをOCR処理
4. 結果をJSON、CSV、Excelとして出力
"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdf_to_images import pdf_to_images
from rotate_images import rotate_image_clockwise
from common import process_invoice_page
from json_to_csv_excel import load_all_json_files, convert_to_dataframe, save_to_csv_and_excel
from page_config import load_pages_config
from config import (
    DATA_DIR,
    RESULTS_IMAGES_DIR,
    RESULTS_JSON_DIR,
    RESULTS_SUMMARY_DIR,
    ocr_worker_count,
    page_image_path,
)
from logging_utils import get_app_logger


def process_pdf(pdf_file):
    logger = get_app_logger()
    logger.info("=" * 60)
    logger.info("納品書OCR処理システム")
    logger.info("=" * 60)
    logger.info("Processing: %s", pdf_file)

    try:
        pages_config = load_pages_config(pdf_file)
    except Exception as e:
        logger.error("Error loading page config: %s", e)
        return 1

    try:
        pdf_to_images(pdf_file, output_dir=RESULTS_IMAGES_DIR, image_format="jpg")
    except Exception as e:
        logger.error("Error during PDF conversion: %s", e)
        return 1

    # ステップ2: 必要なページを回転
    logger.info("[Step 2] 画像の回転処理中...")
    for page_config in pages_config:
        if not page_config.rotate_clockwise:
            continue

        image_path = page_image_path(page_config.page)
        if image_path.exists():
            try:
                rotate_image_clockwise(str(image_path))
            except Exception as e:
                logger.warning("Failed to rotate %s: %s", image_path.name, e)

    # ステップ3: OCR処理
    logger.info("[Step 3] OCR処理中...")

    results = {}
    max_workers = ocr_worker_count(len(pages_config))
    logger.info("Thread count: %s", max_workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                process_invoice_page,
                page_config.page,
                page_config.is_multiple,
                False,
            ): page_config
            for page_config in pages_config
        }

        for future in as_completed(future_map):
            page_config = future_map[future]
            logger.info("Completed page_%s", page_config.page)
            success, data = future.result()
            results[f"page_{page_config.page}"] = {"success": success, "data": data}

            if not success:
                logger.warning("page_%s の処理に失敗しました", page_config.page)
                logger.warning("%s", data)

    # OCR結果サマリー
    success_count = sum(1 for r in results.values() if r["success"])
    logger.info("OCR処理完了: %s/%s ページ", success_count, len(pages_config))

    for page_name in sorted(results.keys()):
        result = results[page_name]
        status = "[OK]" if result["success"] else "[NG]"
        logger.info("%s %s", status, page_name)

    if success_count == 0:
        logger.error("OCR処理が1つも成功しませんでした")
        return 1

    # ステップ4: CSV/Excel出力
    logger.info("[Step 4] CSV/Excel生成中...")

    try:
        # 全JSONファイルを読み込み
        all_data = load_all_json_files(RESULTS_JSON_DIR)
        logger.info("Total records: %s", len(all_data))

        if not all_data:
            logger.warning("データが見つかりませんでした")
            return 1

        # DataFrameに変換
        df = convert_to_dataframe(all_data)

        # CSV/Excel保存
        csv_file, excel_file = save_to_csv_and_excel(df, RESULTS_SUMMARY_DIR)

        logger.info("CSV: %s", csv_file)
        logger.info("Excel: %s", excel_file)

    except Exception as e:
        logger.exception("Error during CSV/Excel generation: %s", e)
        import traceback
        traceback.print_exc()
        return 1

    # 完了
    logger.info("=" * 60)
    logger.info("処理が完了しました")
    logger.info("=" * 60)
    logger.info("画像ファイル: %s/page_*.jpg", RESULTS_IMAGES_DIR)
    logger.info("JSONファイル: %s/page_*_result.json", RESULTS_JSON_DIR)
    logger.info("CSVファイル: %s/all_invoices.csv", RESULTS_SUMMARY_DIR)
    logger.info("Excelファイル: %s/all_invoices.xlsx", RESULTS_SUMMARY_DIR)

    return 0


def main():
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))

    if not pdf_files:
        get_app_logger().error("dataディレクトリにPDFファイルが見つかりません")
        return 1

    if len(pdf_files) > 1:
        get_app_logger().warning("複数のPDFファイルが見つかりました。最初のファイルを処理します。")

    return process_pdf(pdf_files[0])


if __name__ == "__main__":
    sys.exit(main())
