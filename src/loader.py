"""
loader.py: 図面読み込みおよび画像分割・前処理モジュール
PDFや画像ファイルを読み込み、必要に応じてタイル状に分割して返す。
"""

import os

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image


def load_drawing(file_path: str) -> cv2.Mat:
    """指定されたファイル（画像またはPDF）を読み込み、OpenCV形式の画像として返す。

    PDFの場合は1ページ目を画像に変換する。
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"指定されたファイルが見つかりません: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".pdf"]:
        doc = fitz.open(file_path)
        page = doc[0]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        temp_img_path = "temp_page.png"
        pix.save(temp_img_path)

        pil_img = Image.open(temp_img_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        print(f"[Loader] PDFを読み込みました: {file_path} (1ページ目)")
        return img

    elif ext in [".jpg", ".jpeg", ".png", ".tif", ".tiff"]:
        try:
            pil_img = Image.open(file_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception:  # noqa: BLE001
            raise ValueError(f"画像の読み込みに失敗しました: {file_path}")

        print(f"[Loader] 画像ファイルを読み込みました: {file_path}")
        return img

    else:
        raise ValueError(f"サポートされていないファイル形式です: {ext}")


def preprocess_image(img: cv2.Mat) -> cv2.Mat:
    """通常の画像前処理（そのまま返す、または必要に応じた調整）."""
    print("[Loader] 画像の読み込み・前処理が完了しました。")
    return img


def split_image_to_tiles(
    img: cv2.Mat, rows: int = 2, cols: int = 2
) -> list[tuple[cv2.Mat, int, int]]:
    """高精度化のため、画像を指定されたグリッド（rows x cols）に分割（クロップ）する。

    Returns:
        List[Tuple[cv2.Mat, int, int]]: (分割画像, 行インデックス, 列インデックス) のリスト
    """
    h, w, _ = img.shape
    tile_h = h // rows
    tile_w = w // cols
    tiles = []

    for r in range(rows):
        for c in range(cols):
            start_y = r * tile_h
            # 最後の行・列は余りをすべて含める
            end_y = (r + 1) * tile_h if r < rows - 1 else h
            start_x = c * tile_w
            end_x = (c + 1) * tile_w if c < cols - 1 else w

            tile = img[start_y:end_y, start_x:end_x]
            tiles.append((tile, r, c))

    print(f"[Loader] 画像を {rows}x{cols} = {len(tiles)} 分割（タイル化）しました。")
    return tiles
