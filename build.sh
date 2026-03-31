#!/bin/bash
# ============================================================
# AI 教學計畫系統 — 生產環境建置腳本
# ============================================================

set -e

echo "============================================================"
echo "  AI 教學計畫系統 — 生產環境建置"
echo "============================================================"
echo ""

# ------ 後端檢查 ------
echo "[後端] 檢查環境..."

if [ ! -d "backend/venv" ]; then
    echo "  建立虛擬環境..."
    python3 -m venv backend/venv
fi

echo "  安裝後端套件..."
source backend/venv/bin/activate
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q

# 安裝生產用 ASGI 伺服器
pip install gunicorn -q

deactivate
echo "  ✓ 後端準備完成"

echo ""

# ------ 前端建置 ------
echo "[前端] 建置生產版本..."

cd frontend

if [ ! -d "node_modules" ]; then
    echo "  安裝前端套件..."
    npm install --legacy-peer-deps --silent
fi

echo "  執行 next build..."
npm run build

cd ..

echo "  ✓ 前端建置完成"

echo ""
echo "============================================================"
echo "  ✅ 生產環境建置完成"
echo "============================================================"
echo ""
echo "啟動方式："
echo ""
echo "  後端（使用 Gunicorn）："
echo "    cd backend"
echo "    source venv/bin/activate"
echo "    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
echo ""
echo "  前端（使用 Next.js 生產伺服器）："
echo "    cd frontend"
echo "    npm start"
echo ""
