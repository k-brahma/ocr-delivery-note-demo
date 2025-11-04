#!/usr/bin/env python3
"""
指定した画像を時計回りに90度回転するスクリプト
"""
from pathlib import Path
from PIL import Image


def rotate_image_clockwise(image_path: str):
    """
    画像を時計回りに90度回転して上書き保存

    Args:
        image_path: 画像ファイルのパス
    """
    img = Image.open(image_path)
    # PILのrotateは反時計回りなので、時計回りにするには-90度
    rotated = img.rotate(-90, expand=True)
    rotated.save(image_path)
    print(f"Rotated: {image_path}")


def main():
    data_dir = Path("data")

    # page_6とpage_7を回転
    for page_num in [6, 7]:
        image_path = data_dir / f"page_{page_num}.jpeg"
        if image_path.exists():
            rotate_image_clockwise(str(image_path))
        else:
            print(f"Warning: {image_path} not found")

    print("\nRotation completed!")


if __name__ == "__main__":
    main()
