#!/usr/bin/env python3
"""
results/ディレクトリ内のJSONファイルを読み込んで、
1つのCSVとExcelファイルに変換するスクリプト
"""
import json
from pathlib import Path
import pandas as pd


def load_all_json_files(results_dir: str = "results"):
    """
    resultsディレクトリ内の全JSONファイルを読み込む

    Args:
        results_dir: JSONファイルがあるディレクトリ

    Returns:
        list: 全ての納品書データのリスト
    """
    results_path = Path(results_dir)
    all_data = []

    # JSONファイルを読み込み
    json_files = sorted(results_path.glob("page_*_result.json"))

    for json_file in json_files:
        print(f"Loading {json_file.name}...")
        with open(json_file, "r", encoding="utf-8") as f:
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


def save_to_csv_and_excel(df, output_dir: str = "results"):
    """
    DataFrameをCSVとExcelファイルに保存

    Args:
        df: pandas DataFrame
        output_dir: 出力ディレクトリ

    Returns:
        tuple: (CSVファイルパス, Excelファイルパス)
    """
    output_path = Path(output_dir)

    # CSVファイルとして保存
    csv_file = output_path / "all_invoices.csv"
    df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"CSV saved: {csv_file}")

    # Excelファイルとして保存
    excel_file = output_path / "all_invoices.xlsx"
    df.to_excel(excel_file, index=False, engine="openpyxl")
    print(f"Excel saved: {excel_file}")

    return csv_file, excel_file


def main():
    print("=== JSON to CSV/Excel Converter ===\n")

    # 全JSONファイルを読み込み
    all_data = load_all_json_files("results")
    print(f"\nTotal records loaded: {len(all_data)}")

    if not all_data:
        print("No data found in results directory.")
        return

    # DataFrameに変換
    df = convert_to_dataframe(all_data)

    # データフレームの概要を表示
    print("\n=== Data Summary ===")
    print(df.head())
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # CSVとExcelに保存
    print("\n=== Saving to CSV and Excel ===")
    csv_file, excel_file = save_to_csv_and_excel(df, "results")

    print("\n=== Conversion completed! ===")
    print(f"CSV: {csv_file}")
    print(f"Excel: {excel_file}")


if __name__ == "__main__":
    main()
