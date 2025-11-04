#!/usr/bin/env python3
"""
全ページの納品書データを一括抽出するスクリプト
"""
from common import process_invoice_page


def main():
    # 各ページの設定 (ページ番号, 複数納品書フラグ)
    pages = [
        (1, True),   # page_1: 3つの納品書
        (2, False),  # page_2: 1つの納品書
        (3, True),   # page_3: 2つの納品書
        (4, False),  # page_4: 1つの納品書
        (5, True),   # page_5: 2つの納品書
        (6, False),  # page_6: 1つの納品書
        (7, False),  # page_7: 1つの納品書
    ]

    print("=== 全ページの納品書データを抽出します ===\n")

    results = {}
    for page_num, is_multiple in pages:
        print(f"\n--- Page {page_num} ---")
        success, data = process_invoice_page(page_num, is_multiple)
        results[f"page_{page_num}"] = {"success": success, "data": data}

    # 結果サマリー
    print("\n\n=== 処理結果サマリー ===")
    success_count = sum(1 for r in results.values() if r["success"])
    print(f"成功: {success_count}/{len(pages)} ページ")

    for page_name, result in results.items():
        status = "[OK]" if result["success"] else "[NG]"
        print(f"{status} {page_name}")


if __name__ == "__main__":
    main()
