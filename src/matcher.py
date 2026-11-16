"""matcher.py: 部品マスタ照合・金額計算・自己学習モジュール（厳格照合版）

抽出された部品情報と単価マスタを照合し、
1. 短縮記号（M, BC, TB等）が長い型番に巻き込まれない厳格な完全一致・前方一致マッチング
2. EOL（生産終了品）・汎用代替候補の正確な自動補完
3. 未登録部品のマスタへの自動追記学習（自己学習機能）
を実行する。
"""

import logging
import os
from typing import Any

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 実務知見に基づくドメイン置換・代替品アドバイス辞書（正規化キー: 情報）
DOMAIN_ALTERNATIVES: dict[str, dict[str, str]] = {
    "HI10E": {
        "part_name": "電磁接触器（CM・OM）",
        "maker": "安川電機（生産終了）",
        "note": "【EOL代替候補】富士電機: SC-0(SC-03) / 三菱電機: S-N11(S-T10)",
    },
    "HE10S": {
        "part_name": "電磁接触器（CM・OM）",
        "maker": "安川電機（生産終了）",
        "note": "【EOL代替候補】富士電機: SC-0(SC-03) / 三菱電機: S-N11(S-T10)",
    },
    "HI10E5": {
        "part_name": "電磁接触器（CM・OM）",
        "maker": "安川電機（生産終了）",
        "note": "【EOL代替候補】富士電機: SC-0(SC-03) / 三菱電機: S-N11(S-T10)",
    },
    "MSNS": {
        "part_name": "シャッター開閉機用制御盤",
        "maker": "文化シヤッター",
        "note": "専用部品のため純正窓口・専門業者手配（現行制御盤リニューアル検討）",
    },
    "KS": {
        "part_name": "ナイフスイッチ・ヒューズ（3P 15A）",
        "maker": "汎用規格品",
        "note": "【代替候補】NFB 3P 15A（三菱 NF30-CS / 富士 BW32AAG-3P015）へ置換可",
    },
    "FS": {
        "part_name": "ヒューズ・ナイフスイッチ（3P 15A）",
        "maker": "汎用規格品",
        "note": "【代替候補】NFB 3P 15A（三菱 NF30-CS / 富士 BW32AAG-3P015）へ置換可",
    },
}


class PartsMatcher:
    """抽出された部品テキストと単価マスタを突合・集計・自己学習するクラス。"""

    def __init__(self, master_file_path: str, auto_learn: bool = True):
        """初期化処理.

        Args:
            master_file_path (str): 部品単価マスタのファイルパス
            auto_learn (bool): 未登録部品を自動でマスタに追記学習するかどうか
        """
        self.master_file_path = master_file_path
        self.auto_learn = auto_learn
        logger.info("[Matcher] 単価マスタを読み込んでいます: %s", master_file_path)
        self.master_df = self._load_master(master_file_path)

    def _load_master(self, file_path: str) -> pd.DataFrame:
        """単価マスタファイルを安全に読み込む."""
        if not os.path.exists(file_path):
            logger.warning(
                "[Matcher] マスタファイルが存在しないため新規作成します: %s", file_path
            )
            return pd.DataFrame(
                columns=[
                    "検索キーワード",
                    "正式型番",
                    "部品名",
                    "メーカー",
                    "標準単価",
                    "備考・代替候補",
                    "学習ステータス",
                ]
            )

        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        elif file_path.endswith(".csv"):
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="cp932")
        else:
            raise ValueError(f"サポートされていないマスタファイル形式です: {file_path}")

        logger.info(
            "[Matcher] マスタ読み込み完了: %d件のレコードを取得しました。", len(df)
        )
        return df

    def get_known_keywords(self, limit: int = 60) -> list[str]:
        """マスタ登録済みおよびドメイン辞書の型番・キーワード一覧を取得（AIプロンプト注入用）."""
        keywords: list[str] = ["HI-10E", "HE-10S", "MS-NS", "KS", "FS", "3点押釦"]
        if not self.master_df.empty:
            for col in ["正式型番", "検索キーワード"]:
                if col in self.master_df.columns:
                    keywords.extend(
                        self.master_df[col].dropna().astype(str).str.strip().tolist()
                    )
        return list(dict.fromkeys(k for k in keywords if k))[:limit]

    def match_parts(self, extracted_items: list[dict[str, Any]]) -> pd.DataFrame:
        """抽出されたテキストリストを単価マスタと厳格に照合し、未登録部品を自動学習する."""
        logger.info("[Matcher] 部品マスタとの厳格な照合・突合処理を開始します...")

        matched_records: list[dict[str, Any]] = []
        new_unregistered_records: list[dict[str, Any]] = []

        for item in extracted_items:
            text = item.get("text", "").strip()
            ai_part_name = item.get("part_name", "不明")
            ai_maker = item.get("maker", "不明")
            quantity = item.get("quantity", 1)
            confidence = item.get("confidence", 0.9)

            norm_text = text.replace("-", "").replace(" ", "").upper()
            domain_info = DOMAIN_ALTERNATIVES.get(norm_text, {})

            # AIの抽出結果が「不明」の場合はドメイン辞書から補完
            resolved_part_name = (
                ai_part_name
                if ai_part_name != "不明"
                else domain_info.get("part_name", "不明")
            )
            resolved_maker = (
                ai_maker if ai_maker != "不明" else domain_info.get("maker", "不明")
            )
            note = domain_info.get("note", "")

            matched_row = pd.DataFrame()

            if not self.master_df.empty:
                for col in ["検索キーワード", "正式型番"]:
                    if col in self.master_df.columns:
                        col_series = (
                            self.master_df[col]
                            .astype(str)
                            .str.replace("-", "", regex=False)
                            .str.replace(" ", "", regex=False)
                            .str.upper()
                        )
                        # 1. 厳格な完全一致を最優先で検索
                        matched_row = self.master_df[col_series == norm_text]
                        if not matched_row.empty:
                            break

                        # 2. 完全一致しない場合のみ、記号の巻き込みを防ぐため前方一致（または個別定義）を検証
                        # ※ 短すぎる記号（1〜2文字: M, BC, TB 等）は誤部分一致を防ぐため完全一致のみとする
                        if len(norm_text) > 2:
                            cond_contains = col_series.str.contains(
                                norm_text, regex=False, na=False
                            )
                            matched_row = self.master_df[cond_contains]
                            if not matched_row.empty:
                                break

            if not matched_row.empty:
                master_info = matched_row.iloc[0]
                unit_price = float(
                    master_info.get("単価", master_info.get("標準単価", 0.0)) or 0.0
                )
                master_note = str(master_info.get("備考・代替候補", "")).strip()
                if master_note and master_note != "nan":
                    note = master_note

                status_flag = "OK" if unit_price > 0 else "要単価設定（学習済）"

                record = {
                    "検出テキスト": text,
                    "正式型番": master_info.get("正式型番", text),
                    "部品名": master_info.get("部品名", resolved_part_name),
                    "メーカー": master_info.get("メーカー", resolved_maker),
                    "数量": quantity,
                    "単価": unit_price,
                    "小計": quantity * unit_price,
                    "確認フラグ": status_flag,
                    "信頼度": confidence,
                    "備考・代替候補": note,
                }
            else:
                final_part_name = (
                    resolved_part_name
                    if resolved_part_name != "不明"
                    else "要確認（未登録部品）"
                )
                final_maker = resolved_maker if resolved_maker != "不明" else "要確認"

                record = {
                    "検出テキスト": text,
                    "正式型番": text,
                    "部品名": final_part_name,
                    "メーカー": final_maker,
                    "数量": quantity,
                    "単価": 0.0,
                    "小計": 0.0,
                    "確認フラグ": "新規学習（要確認）",
                    "信頼度": confidence,
                    "備考・代替候補": note,
                }

                # 信頼度が0.75以上の未登録部品を自動学習キューに追加
                if self.auto_learn and confidence >= 0.75:
                    new_unregistered_records.append(
                        {
                            "検索キーワード": text,
                            "正式型番": text,
                            "部品名": (
                                resolved_part_name
                                if resolved_part_name != "不明"
                                else "未分類部品"
                            ),
                            "メーカー": (
                                resolved_maker if resolved_maker != "不明" else "不明"
                            ),
                            "標準単価": 0.0,
                            "備考・代替候補": note,
                            "学習ステータス": "自動追加（仮登録）",
                        }
                    )

            matched_records.append(record)

        # 未登録部品をマスタファイルへ自動追記・保存
        if self.auto_learn and new_unregistered_records:
            self._save_learned_parts(new_unregistered_records)

        df_result = pd.DataFrame(matched_records)
        logger.info("[Matcher] 照合完了: %d件の明細を作成しました。", len(df_result))
        return df_result

    def _save_learned_parts(self, new_records: list[dict[str, Any]]) -> None:
        """新規検出された部品を重複チェックの上でマスタファイルへ追記保存する."""
        new_df = pd.DataFrame(new_records).drop_duplicates(subset=["正式型番"])

        if not self.master_df.empty and "正式型番" in self.master_df.columns:
            existing_models = set(
                self.master_df["正式型番"]
                .astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.upper()
            )
            norm_new = (
                new_df["正式型番"]
                .astype(str)
                .str.replace("-", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.upper()
            )
            new_df = new_df[~norm_new.isin(existing_models)]

        if new_df.empty:
            return

        updated_df = pd.concat([self.master_df, new_df], ignore_index=True)

        try:
            os.makedirs(os.path.dirname(self.master_file_path) or ".", exist_ok=True)
            if self.master_file_path.endswith((".xlsx", ".xls")):
                updated_df.to_excel(self.master_file_path, index=False)
            elif self.master_file_path.endswith(".csv"):
                updated_df.to_csv(
                    self.master_file_path, index=False, encoding="utf-8-sig"
                )

            self.master_df = updated_df
            logger.info(
                "[Matcher] 自己学習完了: %d件の未登録部品をマスタへ自動追加しました -> %s",
                len(new_df),
                new_df["正式型番"].tolist(),
            )
        except PermissionError:
            logger.error(
                "[Matcher] マスタファイルが開かれているため自動学習の保存をスキップしました: %s",
                self.master_file_path,
            )
