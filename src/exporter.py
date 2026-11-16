"""exporter.py: BOM帳票出力モジュール

明細データおよびサマリーデータを受け取り、
メーカー名列を含む2面構成のBOM Excelファイルおよび確認用JSONを出力する。
"""

import json
import logging
import os

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

logger = logging.getLogger(__name__)


class BOMExporter:
    """BOM（部品表）をExcelやJSON形式で出力するクラス。"""

    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = output_dir
        self.excel_dir = os.path.join(output_dir, "excel")
        self.json_dir = os.path.join(output_dir, "json")

        os.makedirs(self.excel_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

    def export_to_excel(
        self, df_details: pd.DataFrame, df_summary: pd.DataFrame, base_filename: str
    ) -> str:
        """明細シートとサマリーシートを持つ2面構成のBOM Excelを出力する."""
        output_path = os.path.join(self.excel_dir, f"BOM_{base_filename}.xlsx")
        logger.info("[Exporter] BOM Excelを出力しています: %s", output_path)

        wb = openpyxl.Workbook()
        thin_border = Border(
            left=Side(style="thin", color="D9D9D9"),
            right=Side(style="thin", color="D9D9D9"),
            top=Side(style="thin", color="D9D9D9"),
            bottom=Side(style="thin", color="D9D9D9"),
        )
        header_fill = PatternFill(
            start_color="1F4E78", end_color="1F4E78", fill_type="solid"
        )

        # ==========================================
        # シート1：抽出部品明細一覧
        # ==========================================
        ws1 = wb.active
        ws1.title = "抽出部品明細一覧"

        ws1["B2"] = "【回路図 部品抽出明細一覧】"
        ws1["B2"].font = Font(name="Meiryo UI", size=14, bold=True)

        headers1 = [
            "No",
            "カテゴリ",
            "メーカー名",
            "検出テキスト",
            "正式型番",
            "検索キーワード",
            "数量",
            "信頼度",
            "パーツ検索",
        ]
        for col_idx, h in enumerate(headers1, start=2):
            cell = ws1.cell(row=4, column=col_idx, value=h)
            cell.font = Font(name="Meiryo UI", size=10, bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row_idx = 5
        for _, row in df_details.iterrows():
            link_formula = f'=HYPERLINK("{row["検索URL"]}", "🔍 パーツを探す")'
            row_data = [
                row["No"],
                row["カテゴリ"],
                row["メーカー名"],
                row["検出テキスト"],
                row["正式型番"],
                row["検索キーワード"],
                row["数量"],
                row["信頼度"],
                link_formula,
            ]
            for col_idx, val in enumerate(row_data, start=2):
                cell = ws1.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
                cell.font = Font(name="Meiryo UI", size=9 if col_idx == 10 else 10)
                if col_idx == 10:
                    cell.font = Font(
                        name="Meiryo UI", size=9, color="0563C1", underline="single"
                    )
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx in [2, 8]:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    if col_idx == 8:
                        cell.number_format = "#,##0"
                elif col_idx == 9:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = "0.000"
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
            row_idx += 1

        # ==========================================
        # シート2：同一定数・カテゴリ別サマリー
        # ==========================================
        ws2 = wb.create_sheet(title="同一定数サマリー")

        ws2["B2"] = "【同一定数・カテゴリ別 部品集約サマリー】"
        ws2["B2"].font = Font(name="Meiryo UI", size=14, bold=True)

        headers2 = [
            "No",
            "カテゴリ",
            "メーカー名",
            "正式型番",
            "検索キーワード",
            "総数量",
            "平均信頼度",
            "パーツ検索",
        ]
        for col_idx, h in enumerate(headers2, start=2):
            cell = ws2.cell(row=4, column=col_idx, value=h)
            cell.font = Font(name="Meiryo UI", size=10, bold=True, color="FFFFFF")
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row_idx = 5
        for _, row in df_summary.iterrows():
            link_formula = f'=HYPERLINK("{row["検索URL"]}", "🔍 パーツを探す")'
            row_data = [
                row["No"],
                row["カテゴリ"],
                row["メーカー名"],
                row["正式型番"],
                row["検索キーワード"],
                row["数量"],
                row["信頼度"],
                link_formula,
            ]
            for col_idx, val in enumerate(row_data, start=2):
                cell = ws2.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
                cell.font = Font(name="Meiryo UI", size=9 if col_idx == 9 else 10)
                if col_idx == 9:
                    cell.font = Font(
                        name="Meiryo UI", size=9, color="0563C1", underline="single"
                    )
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx in [2, 7]:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    if col_idx == 7:
                        cell.number_format = "#,##0"
                elif col_idx == 8:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = "0.000"
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
            row_idx += 1

        # 列幅の自動調整（HYPERLINK数式による冗長な広がりを抑制する補正）
        for ws in [ws1, ws2]:
            for col in ws.columns:
                max_len = 0
                for cell in col:
                    val_str = str(cell.value or "")
                    if val_str.startswith("=HYPERLINK"):
                        cell_len = 16
                    else:
                        cell_len = len(val_str)
                    max_len = max(max_len, cell_len)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
        logger.info("[Exporter] BOM Excelの出力が完了しました: %s", output_path)
        return output_path

    def export_to_json(
        self, df_details: pd.DataFrame, df_summary: pd.DataFrame, base_filename: str
    ) -> str:
        output_path = os.path.join(self.json_dir, f"Result_{base_filename}.json")
        output_data = {
            "source_file": base_filename,
            "total_raw_items": len(df_details),
            "total_summary_items": len(df_summary),
            "details": df_details.to_dict(orient="records"),
            "summary": df_summary.to_dict(orient="records"),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        return output_path
