@echo off
chcp 65001 > nul
echo 【システム初期セットアップ】Python仮想環境を作成しています...

REM Pythonの仮想環境(venv)を作成
python -m venv venv

echo 仮想環境を有効化し、必要ライブラリをインストールしています...
call venv\Scripts\activate

REM 必須ライブラリの一括インストール
pip install --upgrade pip
pip install ultralytics easyocr opencv-python PyMuPDF Pillow pandas openpyxl

echo.
echo Setup Complete! セットアップが完了しました。
pause