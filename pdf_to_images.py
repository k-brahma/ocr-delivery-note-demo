#!/usr/bin/env python3
"""
PDFファイルを各ページごとの画像に変換するスクリプト
"""
import os
from pathlib import Path
import fitz  # PyMuPDF


def pdf_to_images(pdf_path: str, output_dir: str = "data", image_format: str = "jpeg"):
    """
    PDFファイルを各ページごとの画像に変換

    Args:
        pdf_path: PDFファイルのパス
        output_dir: 出力ディレクトリ (デフォルト: data)
        image_format: 画像フォーマット (jpeg, png, gif など)
    """
    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # PDFを開く
    print(f"Converting {pdf_path} to images...")
    pdf_document = fitz.open(pdf_path)

    # 各ページを画像として保存
    total_pages = len(pdf_document)
    for page_num in range(total_pages):
        page = pdf_document[page_num]
        # 300 DPIに相当する倍率 (72 DPI * 4.166 ≈ 300 DPI)
        mat = fitz.Matrix(4.166, 4.166)
        pix = page.get_pixmap(matrix=mat)

        output_file = output_path / f"page_{page_num + 1}.{image_format}"
        pix.save(str(output_file))
        print(f"Saved: {output_file}")

    pdf_document.close()
    print(f"\nConversion completed! Total pages: {total_pages}")


def main():
    # pdfディレクトリ内のPDFファイルを検索
    pdf_dir = Path("pdf")
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("Error: No PDF files found in 'pdf' directory")
        return

    if len(pdf_files) > 1:
        print("Warning: Multiple PDF files found. Processing the first one.")

    pdf_file = pdf_files[0]
    print(f"Processing: {pdf_file}\n")

    # PDFを画像に変換
    pdf_to_images(str(pdf_file), output_dir="data", image_format="jpeg")


if __name__ == "__main__":
    main()
