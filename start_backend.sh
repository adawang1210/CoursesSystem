#!/bin/bash
# ============================================================
# AI 教學計畫系統 — 後端啟動腳本
# 自動建立虛擬環境、安裝套件、檢查 .env 後啟動 FastAPI
# ============================================================

set -e

echo "============================================================"
echo "  啟動 AI 教學計畫系統後端"
echo "============================================================"
echo ""

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "[錯誤] 找不到 python3，請先安裝 Python 3.9+"
    exit 1
fi

# 建立虛擬環境（如不存在）
if [ ! -d "backend/venv" ]; then
    echo "[設定] 建立 Python 虛擬環境..."
    python3 -m venv backend/venv
fi

# 進入後端目錄
cd backend

# 啟動虛擬環境
source venv/bin/activate

# 安裝套件
echo "[設定] 安裝後端相依套件..."
pip install -r requirements.txt -q

# 檢查 .env
if [ ! -f ".env" ]; then
    echo ""
    echo "[錯誤] 找不到 .env 檔案"
    echo "  請在 backend/ 目錄建立 .env 檔案"
    echo "  或執行根目錄的 ./setup.sh 自動建立"
    exit 1
fi

echo ""
echo "[啟動] 後端服務啟動中..."
echo "  API 文件：http://localhost:8000/docs"
echo "  健康檢查：http://localhost:8000/health"
echo ""

# 啟動 FastAPI（使用 Uvicorn，開啟 hot-reload）
python -m app.main
