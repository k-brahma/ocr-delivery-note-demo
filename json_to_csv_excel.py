#!/usr/bin/env python3
"""
results/json 内のJSONファイルを読み込んで、
CSVとExcelファイルに変換するスクリプト
"""
import json
from pathlib import Path
import pandas as pd
from config import RESULTS_JSON_DIR, RESULTS_SUMMARY_DIR
from logging_utils import get_app_logger


def load_all_json_files(results_dir: Path = RESULTS_JSON_DIR):
    """
    resultsディレクトリ内の全JSONファイルを読み込む

    Args:
        results_dir: JSONファイルがあるディレクトリ

    Returns:
        list: 全ての納品書データのリスト
    """
    all_data = []

    # JSONファイルを読み込み
    json_files = sorted(results_dir.glob("page_*_result.json"))

    for json_file in json_files:
        get_app_logger().info("Loading JSON: %s", json_file.name)
        with json_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # データが配列の場合はそのまま、単一オブジェクトの場合はリスト化
        if isinstance(data, list):
            for item in data:
                item["ソースファイル"] = json_file.stem
                all_data.append(item)
        else:
            data["ソースファイル"] = json_file.stem
            all_data.append(data)

    return all_data


def convert_to_dataframe(data_list):
    """
    納品書データリストをDataFrameに変換

    Args:
        data_list: 納品書データのリスト

    Returns:
        DataFrame: pandas DataFrame
    """
    df = pd.DataFrame(data_list)

    # カラムの順序を整理
    columns_order = ["ソースファイル", "納品日", "会社名", "品名", "単価", "数量"]
    # 存在するカラムのみ選択
    columns = [col for col in columns_order if col in df.columns]
    df = df[columns]

    return df


def save_to_csv_and_excel(df, output_dir: Path = RESULTS_SUMMARY_DIR):
    """
    DataFrameをCSVとExcelファイルに保存

    Args:
        df: pandas DataFrame
        output_dir: 出力ディレクトリ

    Returns:
        tuple: (CSVファイルパス, Excelファイルパス)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSVファイルとして保存
    csv_file = output_dir / "all_invoices.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    get_app_logger().info("CSV saved: %s", csv_file)

    # Excelファイルとして保存
    excel_file = output_dir / "all_invoices.xlsx"
    df.to_excel(excel_file, index=False, engine="openpyxl")
    get_app_logger().info("Excel saved: %s", excel_file)

    return csv_file, excel_file


def main():
    logger = get_app_logger()
    logger.info("=== JSON to CSV/Excel Converter ===")

    # 全JSONファイルを読み込み
    all_data = load_all_json_files(RESULTS_JSON_DIR)
    logger.info("Total records loaded: %s", len(all_data))

    if not all_data:
        logger.warning("No data found in results/json directory.")
        return

    # DataFrameに変換
    df = convert_to_dataframe(all_data)

    # データフレームの概要を表示
    logger.info("Data Summary:\n%s", df.head())
    logger.info("Total rows: %s", len(df))
    logger.info("Columns: %s", list(df.columns))

    # CSVとExcelに保存
    logger.info("Saving to CSV and Excel")
    csv_file, excel_file = save_to_csv_and_excel(df, RESULTS_SUMMARY_DIR)

    logger.info("Conversion completed")
    logger.info("CSV: %s", csv_file)
    logger.info("Excel: %s", excel_file)


if __name__ == "__main__":
    main()
