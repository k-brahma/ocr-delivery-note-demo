#!/usr/bin/env python3
"""
全ページの納品書データを一括抽出するスクリプト
"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import process_invoice_page
from json_to_csv_excel import load_all_json_files, convert_to_dataframe, save_to_csv_and_excel
from page_config import load_pages_config
from config import DATA_DIR, RESULTS_JSON_DIR, RESULTS_SUMMARY_DIR, ocr_worker_count
from logging_utils import get_app_logger


def main():
    logger = get_app_logger()
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found in data directory")
        return 1

    if len(pdf_files) > 1:
        logger.warning("Multiple PDF files found. Processing the first one.")

    pdf_file = pdf_files[0]
    try:
        pages = load_pages_config(pdf_file)
    except Exception as e:
        logger.error("Error loading page config: %s", e)
        return 1

    logger.info("=== 全ページの納品書データを抽出します ===")

    results = {}
    max_workers = ocr_worker_count(len(pages))
    logger.info("Thread count: %s", max_workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                process_invoice_page,
                page_config.page,
                page_config.is_multiple,
                False,
            ): page_config
            for page_config in pages
        }

        for future in as_completed(future_map):
            page_config = future_map[future]
            logger.info("Completed page_%s", page_config.page)
            success, data = future.result()
            results[f"page_{page_config.page}"] = {"success": success, "data": data}
            if not success:
                logger.warning("page_%s failed", page_config.page)
                logger.warning("%s", data)

    # 結果サマリー
    logger.info("=== 処理結果サマリー ===")
    success_count = sum(1 for r in results.values() if r["success"])
    logger.info("成功: %s/%s ページ", success_count, len(pages))

    for page_name in sorted(results.keys()):
        result = results[page_name]
        status = "[OK]" if result["success"] else "[NG]"
        logger.info("%s %s", status, page_name)

    if success_count == 0:
        return

    all_data = load_all_json_files(RESULTS_JSON_DIR)
    if not all_data:
        logger.warning("No data found in results/json directory.")
        return

    df = convert_to_dataframe(all_data)
    csv_file, excel_file = save_to_csv_and_excel(df, RESULTS_SUMMARY_DIR)
    logger.info("CSV: %s", csv_file)
    logger.info("Excel: %s", excel_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
