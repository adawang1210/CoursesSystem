#!/bin/bash
# AI 教學計畫系統 - 後端啟動腳本

echo "啟動 AI 教學計畫系統後端..."

# 檢查 Python 虛擬環境
if [ ! -d "backend/venv" ]; then
    echo "[警告] 找不到虛擬環境，正在建立..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# 啟動虛擬環境並安裝套件
echo "[資訊] 安裝後端相依套件..."
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 檢查環境變數
if [ ! -f ".env" ]; then
    echo "[錯誤] 找不到 .env 檔案，請先設定環境變數"
    echo "[提示] 請在 backend 目錄建立 .env 檔案"
    exit 1
fi

# 啟動後端服務
echo "[啟動] 後端服務啟動中..."
echo "API 文件：http://localhost:8000/docs"
echo "健康檢查：http://localhost:8000/health"
echo ""

python -m app.main

