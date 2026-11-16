"""classifier.py: カテゴリ自動分類・メーカー名付与・同一定数集約モジュール

抽出された部品テキスト・型番・回路記号をもとに、
カテゴリ大分類への統合、メーカー名の自動判定、および同一定数の集約・カテゴリ別ソート・数値順ソートを行う。
"""

import logging
import re
import urllib.parse

import pandas as pd

logger = logging.getLogger(__name__)


class ComponentClassifier:
    """部品のカテゴリ整理、メーカー名付与、集約、検索クエリ生成を管理するクラス。"""

    def __init__(self, search_site: str = "kura"):
        self.search_site = search_site

    def classify_category(self, text: str, formal_model: str = "") -> str:
        """部品を大分類カテゴリに統合する."""
        target = f"{formal_model} {text}".upper()

        if re.search(r"([0-9.]+\s*(UF|PF|NF|μF|P|F))|( C\d+ )", target, re.IGNORECASE):
            return "受動部品（コンデンサ）"

        if re.search(
            r"([0-9.]+\s*(Ω|OHM|K|M))|( R\d+ )|(VR\d+)", target, re.IGNORECASE
        ):
            return "受動部品（抵抗）"

        if re.search(
            r"(AD|TA|µA|NE|TL|2SC|2SA|2SJ|2SK|RN|IC| Q\d+ | A\d+ )",
            target,
            re.IGNORECASE,
        ):
            return "IC・半導体"

        return "機構・接続部品"

    def detect_maker(self, formal_model: str, text: str) -> str:
        """型番やテキストからメーカー名を推測し、不明な場合は「不明」を返す."""
        target = f"{formal_model} {text}".upper()

        if "AD" in target or "ANALOG DEVICES" in target:
            return "Analog Devices"
        elif "TA" in target and "東芝" in target:
            return "東芝 (Toshiba)"
        elif "TI" in target or "LM" in target or "SN" in target:
            return "Texas Instruments"

        return "不明"

    def generate_search_url(self, search_query: str) -> str:
        """指定された検索サイトのURLスキームに従って検索URLを生成する."""
        encoded_query = urllib.parse.quote(search_query)

        if self.search_site == "kura":
            return f"https://www.kura-denshi.com/view/search?search_keyword={encoded_query}"
        elif self.search_site == "rs":
            return f"https://jp.rs-online.com/web/c/?searchTerm={encoded_query}"
        elif self.search_site == "digikey":
            return f"https://www.digikey.jp/ja/products/result?keywords={encoded_query}"
        else:
            return f"https://www.kura-denshi.com/view/search?search_keyword={encoded_query}"

    def _parse_resistance(self, val_str: str) -> float:
        """抵抗値をオーム単位の数値に変換してソート用に返す."""
        if not val_str:
            return 0.0
        s = str(val_str).upper().replace("Ω", "").replace("OHM", "").strip()
        multiplier = 1.0
        if "K" in s:
            multiplier = 1000.0
            s = s.replace("K", "").strip()
        elif "M" in s:
            multiplier = 1000000.0
            s = s.replace("M", "").strip()
        try:
            return float(s) * multiplier
        except ValueError:
            return 0.0

    def _parse_capacitance(self, val_str: str) -> float:
        """静電容量をピコファラッド単位の数値に変換してソート用に返す."""
        if not val_str:
            return 0.0
        s = str(val_str).upper().strip()
        multiplier = 1.0
        if "UF" in s or "ΜF" in s or "µF" in s:
            multiplier = 1000000.0
            s = s.replace("UF", "").replace("ΜF", "").replace("µF", "").strip()
        elif "NF" in s:
            multiplier = 1000.0
            s = s.replace("NF", "").strip()
        elif "PF" in s or "P" in s:
            multiplier = 1.0
            s = s.replace("PF", "").replace("P", "").strip()
        try:
            return float(s) * multiplier
        except ValueError:
            return 0.0

    def process_components(self, raw_items: list) -> tuple[pd.DataFrame, pd.DataFrame]:
        """抽出された生データを受け取り、集約・数値ソート・カテゴリソート処理を行う."""
        processed_rows = []

        aggregated_counts = {}
        for item in raw_items:
            detected_text = str(item.get("text", item.get("検出テキスト", "")))
            formal_model = str(item.get("formal_model", item.get("正式型番", "")))
            qty = int(item.get("quantity", item.get("数量", 1)))
            confidence = float(item.get("confidence", item.get("信頼度", 0.0)))

            base_query = (
                formal_model
                if formal_model and formal_model != "不明"
                else detected_text
            )
            paren_match = re.search(r"\((.*?)\)", base_query)
            search_query = (
                paren_match.group(1).strip() if paren_match else base_query.strip()
            )

            key = (formal_model, search_query)
            if key in aggregated_counts:
                aggregated_counts[key]["quantity"] += qty
                aggregated_counts[key]["confidence_sum"] += confidence * qty
                aggregated_counts[key]["total_count"] += qty
            else:
                aggregated_counts[key] = {
                    "detected_text": detected_text,
                    "formal_model": formal_model,
                    "search_query": search_query,
                    "quantity": qty,
                    "confidence_sum": confidence * qty,
                    "total_count": qty,
                }

        # 明細行データの構築
        for idx, item in enumerate(raw_items):
            detected_text = str(item.get("text", item.get("検出テキスト", "")))
            formal_model = str(item.get("formal_model", item.get("正式型番", "")))
            qty = int(item.get("quantity", item.get("数量", 1)))
            confidence = float(item.get("confidence", item.get("信頼度", 0.0)))

            base_query = (
                formal_model
                if formal_model and formal_model != "不明"
                else detected_text
            )
            paren_match = re.search(r"\((.*?)\)", base_query)
            search_query = (
                paren_match.group(1).strip() if paren_match else base_query.strip()
            )

            category = self.classify_category(detected_text, formal_model)
            maker = self.detect_maker(formal_model, detected_text)
            search_url = self.generate_search_url(search_query)

            processed_rows.append(
                {
                    "No": idx + 1,
                    "カテゴリ": category,
                    "メーカー名": maker,
                    "検出テキスト": detected_text,
                    "正式型番": formal_model,
                    "検索キーワード": search_query,
                    "数量": qty,
                    "信頼度": round(confidence, 3),
                    "検索URL": search_url,
                }
            )

        df_details = pd.DataFrame(processed_rows)

        # サマリー集約および数値・カテゴリ別ソートの適用
        summary_rows = []
        for key, data in aggregated_counts.items():
            formal_model, search_query = key
            detected_text = data["detected_text"]
            category = self.classify_category(detected_text, formal_model)
            maker = self.detect_maker(formal_model, detected_text)
            search_url = self.generate_search_url(search_query)
            avg_confidence = (
                data["confidence_sum"] / data["total_count"]
                if data["total_count"] > 0
                else 0.0
            )

            if category == "受動部品（抵抗）":
                val_num = self._parse_resistance(formal_model)
            elif category == "受動部品（コンデンサ）":
                val_num = self._parse_capacitance(formal_model)
            else:
                val_num = 0.0

            summary_rows.append(
                {
                    "カテゴリ": category,
                    "メーカー名": maker,
                    "正式型番": formal_model,
                    "検索キーワード": search_query,
                    "数量": data["quantity"],
                    "信頼度": round(avg_confidence, 3),
                    "検索URL": search_url,
                    "_val_num": val_num,
                }
            )

        df_summary = pd.DataFrame(summary_rows)
        if not df_summary.empty:
            category_priority = {
                "IC・半導体": 1,
                "受動部品（抵抗）": 2,
                "受動部品（コンデンサ）": 3,
                "機構・接続部品": 4,
            }
            df_summary["sort_key"] = df_summary["カテゴリ"].map(
                lambda x: category_priority.get(x, 99)
            )

            # カテゴリ順 → 同一カテゴリ内では数値順（小→大）でソート
            df_summary = df_summary.sort_values(
                by=["sort_key", "_val_num", "正式型番"]
            ).drop(columns=["sort_key", "_val_num"])
            df_summary.insert(0, "No", range(1, len(df_summary) + 1))
        else:
            df_summary = pd.DataFrame(
                columns=[
                    "No",
                    "カテゴリ",
                    "メーカー名",
                    "正式型番",
                    "検索キーワード",
                    "数量",
                    "信頼度",
                    "検索URL",
                ]
            )

        return df_details, df_summary
