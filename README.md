# CircuitBOM-Extractor
> 回路図面（PDF/画像）自動解析・BOM自動生成システム

## 📌 システム概要
`CircuitBOM-Extractor` は、電気・電子回路図（PDF / PNG / JPG / TIF）をインプットとして、**Gemini API ビジョンモデル**を活用して部品・型番・定数を高精度に動的抽出し、カテゴリ自動分類、同一定数集約（物理単位換算による数値順昇順ソート）、および調達サイト検索リンク付きの BOM Excel帳票を出力する自動化ツールです。

手作業による目視の拾い出し工数を削減し、転記ミスやカウント漏れを防ぐとともに、設計・調達業務のDXを強力にサポートします。

---

## 🚀 主な機能とアップデート（Rev.2）
1. **Gemini API ビジョンモデルによる画像直接解析**
   * 従来の固定モックや簡易OCR処理から刷新。AIビジョンモデル（`gemini-3.5-flash-lite` 等）により、複雑な回路図面からテキストや部品シンボルをダイレクトかつ高精度に構造化抽出。
2. **抵抗・コンデンサの数値順（小 → 大）昇順ソート機能**
   * サマリー集計時に抵抗値（$\Omega, \text{k}\Omega$）や静電容量（$\text{pF}, \mu\text{F}$）を自動パースして物理単位に換算し、同一カテゴリ内で値の小さい順に正確に並び替え。
3. **Excelレイアウト最適化 & 処理安定化**
   * `HYPERLINK` 数式列の過度な広がりを防ぐ列幅の自動最適化ロジック、およびAPI例外時の堅牢なフォールバック処理を実装。
4. **将来拡張性の担保（CADネットリスト対応）**
   * 将来的なCADネットリスト（EDIF / CSV / XML等）インポートに対応するための拡張プレースホルダーをコード内に実装。

---

## 🛠️ 技術スタック
* **言語**: Python 3.11以上
* **AI・画像解析**: Gemini API (Vision), Ultralytics YOLO, OpenCV, PyMuPDF
* **データ処理・帳票生成**: pandas, openpyxl
* **実行環境**: Windows 11 Pro（オフライン＆セキュアAPI連携のローカル完結設計）

---

## 📂 ディレクトリ構成
```text
CircuitBOM-Extractor/
├── .env                  # APIキーなどの環境設定（※ .gitignore に追加）
├── .gitignore            # Git除外設定 (.env, venv/, outputs/ 等)
├── requirements.txt      # 依存ライブラリ一覧
├── README.md             # システム全体の公式マニュアル
├── main.py               # エントリーポイント
├── src/                  # ソースコード格納フォルダ
│   ├── __init__.py
│   ├── extractor.py      # Gemini API ビジョンモデル抽出モジュール
│   ├── classifier.py     # カテゴリ分類・数値順ソートモジュール
│   └── exporter.py       # BOM Excel / JSON出力モジュール
├── inputs/               # 入力ファイル格納フォルダ（図面画像・PDF）
│   └── drawings/         # 回路図サンプル等
├── outputs/              # 出力ファイル格納フォルダ（BOM Excel・JSON・検証画像）
├── docs/                 # 要件定義書・概要レビュー資料等
└── venv/                 # Python仮想環境（※ .gitignore 対象）
```

---

## ⚙️ セットアップ手順

1. **リポジトリのクローン・移動**
   ```bash
   cd CircuitBOM-Extractor
   ```

2. **依存ライブラリのインストール**
   ```bash
   pip install -s requirements.txt
   ```
   *(主要パッケージ: `pandas`, `openpyxl`, `PyMuPDF`, `opencv-python`, `google-generativeai`)*

3. **APIキーの設定**
   環境変数または設定ファイルに Gemini API キーを設定してください。
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

---

## 🏃‍♂️ 実行方法

対象の図面ファイルを `data/input/drawings/` に配置し、以下のコマンドを実行します。

```bash
python main.py --input data/input/drawings/sample_circuit.pdf
```

### 出力される成果物 (`data/output/`)
* **BOM Excel (`*.xlsx`)**: 明細一覧シート ＋ 同一定数サマリーシート（調達検索リンク、最適化済み列幅）
* **統一JSON (`*.json`)**: 抽出された部品群のテキスト、座標、確信度ログ
* **検証画像 (`*.png`)**: 検出枠を描画した目視確認用図面

