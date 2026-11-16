"""main.py: CircuitBOM-Extractor メインエントリーポイント（フォルダ構成統一・APIキー対応版）

inputs/drawings/ 内の全回路図を対象に、
画像ファイルごとの動的部品抽出（Gemini API連携対応）およびBOM自動生成を一括実行する。
"""

import argparse
import glob
import logging
import os
import sys

from src.classifier import ComponentClassifier
from src.exporter import BOMExporter
from src.extractor import DrawingExtractor

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="CircuitBOM-Extractor: 回路図部品抽出・BOM自動生成システム（動的抽出・APIキー対応版）"
    )
    parser.add_argument(
        "--input",
        default="inputs/drawings",
        help="解析対象の回路図フォルダパス、または個別ファイルパス",
    )
    parser.add_argument("--output", default="outputs", help="出力先ルートディレクトリ")
    parser.add_argument(
        "--site",
        default="kura",
        choices=["kura", "rs", "digikey"],
        help="パーツ検索サイト (kura: KURA電子, rs: RS, digikey: DigiKey)",
    )
    parser.add_argument(
        "--apikey",
        default=None,
        help="Gemini APIキー（省略時は環境変数 GEMINI_API_KEY を使用）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存の出力ファイルがあってもスキップせずに強制再処理する",
    )
    args = parser.parse_args()

    input_target = args.input
    output_dir = args.output

    if os.path.isfile(input_target):
        target_files = [input_target]
    elif os.path.isdir(input_target):
        extensions = ("*.jpg", "*.jpeg", "*.png", "*.tif", "*.pdf")
        target_files = []
        for ext in extensions:
            target_files.extend(glob.glob(os.path.join(input_target, ext)))
    else:
        logger.error("指定された入力パスが存在しません: %s", input_target)
        sys.exit(1)

    if not target_files:
        logger.warning(
            "処理対象の回路図ファイルが見つかりませんでした: %s", input_target
        )
        return

    logger.info("=== CircuitBOM-Extractor 処理開始 (対象: %d件) ===", len(target_files))

    extractor = DrawingExtractor(api_key=args.apikey)
    classifier = ComponentClassifier(search_site=args.site)
    exporter = BOMExporter(output_dir=output_dir)

    processed_count = 0

    for file_path in target_files:
        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        logger.info("--------------------------------------------------")
        logger.info("📄 処理中ファイル: %s", file_path)

        # 動的部品抽出（Gemini API ビジョン解析 / フォールバック）
        raw_extracted_items = extractor.extract_from_image(file_path)

        # カテゴリ分類・同一定数集約・数値順（小→大）昇順ソート
        df_details, df_summary = classifier.process_components(raw_extracted_items)

        # 帳票出力（列幅自動最適化適用）
        excel_path = exporter.export_to_excel(df_details, df_summary, base_filename)
        json_path = exporter.export_to_json(df_details, df_summary, base_filename)

        logger.info("  ✔ 完了 - Excel: %s", excel_path)
        logger.info("  ✔ 完了 - JSON : %s", json_path)
        processed_count += 1

    logger.info("================================================")
    logger.info("🎉 全処理が終了しました (処理: %d件)", processed_count)


if __name__ == "__main__":
    main()
