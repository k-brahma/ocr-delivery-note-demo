#!/usr/bin/env python3
"""
納品書OCR処理の共通モジュール
"""
import os
import json
from pathlib import Path
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv


def extract_invoice_data(image_path: str, is_multiple: bool = False, api_key: str = None):
    """
    画像から納品書データを抽出

    Args:
        image_path: 画像ファイルのパス
        is_multiple: 複数の納品書が含まれている場合True (配列形式で返す)
        api_key: Gemini API Key (.envファイルから取得可能)

    Returns:
        dict or list: 抽出された納品書データ (is_multiple=Trueの場合は配列)
    """
    # .envファイルから環境変数を読み込み
    load_dotenv()

    # API Keyの設定
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in .env file")

    genai.configure(api_key=api_key)

    # モデルの初期化 (gemini-2.5-flash: 安定版の高性能モデル)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 画像を読み込み
    image = Image.open(image_path)

    # プロンプト
    if is_multiple:
        prompt = """
この画像には複数の納品書が含まれています。
各納品書について、以下の情報をJSON配列形式で抽出してください:

[
  {
    "納品日": "日付（yyyy/mm/dd形式）",
    "会社名": "宛先の会社名",
    "品名": "商品・サービスの名前",
    "単価": "1個あたりの価格",
    "数量": "個数"
  },
  ...
]

JSON配列形式のみを返してください。説明文は不要です。
キー名は日本語で「納品日」「会社名」「品名」「単価」「数量」としてください。
納品日は必ずyyyy/mm/dd形式（例: 2025/10/15）で出力してください。
"""
    else:
        prompt = """
この画像は納品書です。以下の情報をJSON形式で抽出してください:

- 納品日: 日付（yyyy/mm/dd形式）
- 会社名: 宛先の会社名
- 品名: 商品・サービスの名前
- 単価: 1個あたりの価格
- 数量: 個数

JSON形式のみを返してください。説明文は不要です。
キー名は日本語で「納品日」「会社名」「品名」「単価」「数量」としてください。
納品日は必ずyyyy/mm/dd形式（例: 2025/10/15）で出力してください。
"""

    # APIリクエスト
    print(f"Analyzing {image_path}...")
    response = model.generate_content([prompt, image])

    # レスポンスからJSONを抽出
    response_text = response.text.strip()

    # マークダウンのコードブロックを除去
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    response_text = response_text.strip()

    # JSONをパース
    data = json.loads(response_text)

    return data


def save_result(data, output_filename: str, results_dir: str = "results"):
    """
    結果をJSONファイルとして保存

    Args:
        data: 保存するデータ
        output_filename: 出力ファイル名
        results_dir: 出力ディレクトリ (デフォルト: results)

    Returns:
        Path: 保存したファイルのパス
    """
    # resultsディレクトリを作成
    results_path = Path(results_dir)
    results_path.mkdir(exist_ok=True)

    # JSONファイルとして保存
    output_path = results_path / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_path


def print_result(data, is_multiple: bool = False):
    """
    結果を表示

    Args:
        data: 表示するデータ
        is_multiple: 複数の納品書データの場合True
    """
    if is_multiple:
        print(f"\n=== 抽出結果 (合計 {len(data)}件) ===")
    else:
        print("\n=== 抽出結果 ===")

    try:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        # Windows環境での文字コードエラー対策
        print(json.dumps(data, ensure_ascii=True, indent=2))


def process_invoice_page(page_number: int, is_multiple: bool = False):
    """
    指定されたページの納品書を処理

    Args:
        page_number: ページ番号
        is_multiple: 複数の納品書が含まれている場合True

    Returns:
        tuple: (成功フラグ, データ or エラーメッセージ)
    """
    # 対象画像
    image_path = Path(f"data/page_{page_number}.jpeg")

    if not image_path.exists():
        return False, f"Error: {image_path} not found"

    try:
        # 納品書データを抽出
        invoice_data = extract_invoice_data(str(image_path), is_multiple=is_multiple)

        # 結果を表示
        print_result(invoice_data, is_multiple=is_multiple)

        # 結果を保存
        output_path = save_result(invoice_data, f"page_{page_number}_result.json")

        print(f"\n結果を保存しました: {output_path}")

        return True, invoice_data

    except Exception as e:
        import traceback
        error_msg = f"Error: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return False, error_msg
