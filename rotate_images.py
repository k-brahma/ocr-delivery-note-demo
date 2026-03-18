#!/usr/bin/env python3
"""
指定した画像を時計回りに90度回転するスクリプト
"""
from PIL import Image
from config import page_image_path
from logging_utils import get_app_logger


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
    get_app_logger().info("Rotated image: %s", image_path)


def main():
    # page_6とpage_7を回転
    for page_num in [6, 7]:
        image_path = page_image_path(page_num)
        if image_path.exists():
            rotate_image_clockwise(str(image_path))
        else:
            get_app_logger().warning("%s not found", image_path)

    get_app_logger().info("Rotation completed")


if __name__ == "__main__":
    main()
