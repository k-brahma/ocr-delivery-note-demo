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
from pathlib import Path
from pdf_to_images import pdf_to_images
from rotate_images import rotate_image_clockwise
from common import process_invoice_page
from json_to_csv_excel import load_all_json_files, convert_to_dataframe, save_to_csv_and_excel


def main():
    print("=" * 60)
    print("納品書OCR処理システム")
    print("=" * 60)

    # ステップ1: PDFを画像に変換
    print("\n[Step 1] PDFを画像に変換中...")
    pdf_dir = Path("pdf")
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("Error: pdfディレクトリにPDFファイルが見つかりません")
        return 1

    if len(pdf_files) > 1:
        print("Warning: 複数のPDFファイルが見つかりました。最初のファイルを処理します。")

    pdf_file = pdf_files[0]
    print(f"Processing: {pdf_file}")

    try:
        pdf_to_images(str(pdf_file), output_dir="data", image_format="jpeg")
    except Exception as e:
        print(f"Error during PDF conversion: {e}")
        return 1

    # ステップ2: 必要なページを回転
    print("\n[Step 2] 画像の回転処理中...")
    rotate_pages = [6, 7]  # page_6とpage_7を回転
    for page_num in rotate_pages:
        image_path = Path(f"data/page_{page_num}.jpeg")
        if image_path.exists():
            try:
                rotate_image_clockwise(str(image_path))
                print(f"Rotated: page_{page_num}.jpeg")
            except Exception as e:
                print(f"Warning: Failed to rotate page_{page_num}.jpeg: {e}")

    # ステップ3: OCR処理
    print("\n[Step 3] OCR処理中...")

    # 各ページの設定 (ページ番号, 複数納品書フラグ)
    pages_config = [
        (1, True),   # page_1: 3つの納品書
        (2, False),  # page_2: 1つの納品書
        (3, True),   # page_3: 2つの納品書
        (4, False),  # page_4: 1つの納品書
        (5, True),   # page_5: 2つの納品書
        (6, False),  # page_6: 1つの納品書
        (7, False),  # page_7: 1つの納品書
    ]

    results = {}
    for page_num, is_multiple in pages_config:
        print(f"\n  Processing page_{page_num}...")
        success, data = process_invoice_page(page_num, is_multiple)
        results[f"page_{page_num}"] = {"success": success, "data": data}

        if not success:
            print(f"  Warning: page_{page_num} の処理に失敗しました")

    # OCR結果サマリー
    success_count = sum(1 for r in results.values() if r["success"])
    print(f"\n  OCR処理完了: {success_count}/{len(pages_config)} ページ")

    for page_name, result in results.items():
        status = "[OK]" if result["success"] else "[NG]"
        print(f"  {status} {page_name}")

    if success_count == 0:
        print("\nError: OCR処理が1つも成功しませんでした")
        return 1

    # ステップ4: CSV/Excel出力
    print("\n[Step 4] CSV/Excel生成中...")

    try:
        # 全JSONファイルを読み込み
        all_data = load_all_json_files("results")
        print(f"  Total records: {len(all_data)}")

        if not all_data:
            print("  Warning: データが見つかりませんでした")
            return 1

        # DataFrameに変換
        df = convert_to_dataframe(all_data)

        # CSV/Excel保存
        csv_file, excel_file = save_to_csv_and_excel(df, "results")

        print(f"\n  CSV: {csv_file}")
        print(f"  Excel: {excel_file}")

    except Exception as e:
        print(f"Error during CSV/Excel generation: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 完了
    print("\n" + "=" * 60)
    print("処理が完了しました！")
    print("=" * 60)
    print(f"\n出力ファイル:")
    print(f"  - JSONファイル: results/page_*_result.json")
    print(f"  - CSVファイル: results/all_invoices.csv")
    print(f"  - Excelファイル: results/all_invoices.xlsx")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
