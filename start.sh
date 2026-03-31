#!/bin/bash
# ============================================================
# AI 教學計畫系統 — 同時啟動前後端
# 使用背景程序同時運行，按 Ctrl+C 可一次停止全部
# ============================================================

set -e

echo "============================================================"
echo "  AI 教學計畫系統 — 啟動中"
echo "============================================================"
echo ""

# 確認 MongoDB 是否可連線
echo "[檢查] MongoDB 連線..."
if command -v mongosh &> /dev/null; then
    if mongosh --eval "db.runCommand({ping:1})" --quiet mongodb://localhost:27017 &> /dev/null; then
        echo "  ✓ MongoDB 連線正常"
    else
        echo "  ⚠ 無法連線至 MongoDB，請確認服務已啟動"
        echo "    macOS: brew services start mongodb-community@7.0"
        echo "    Linux: sudo systemctl start mongod"
    fi
else
    echo "  ⚠ 未安裝 mongosh，跳過連線檢查"
fi

echo ""

# 儲存子程序 PID 以便清理
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "[停止] 正在關閉所有服務..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo "  ✓ 所有服務已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ------ 啟動後端 ------
echo "[啟動] 後端服務 (port 8000)..."

if [ ! -d "backend/venv" ]; then
    echo "  ⚠ 找不到虛擬環境，請先執行 ./setup.sh"
    exit 1
fi

if [ ! -f "backend/.env" ]; then
    echo "  ⚠ 找不到 backend/.env，請先執行 ./setup.sh"
    exit 1
fi

(
    cd backend
    source venv/bin/activate
    python -m app.main
) &
BACKEND_PID=$!

# 等待後端啟動
sleep 3

# ------ 啟動前端 ------
echo "[啟動] 前端服務 (port 3000)..."

if [ ! -d "frontend/node_modules" ]; then
    echo "  安裝前端套件..."
    (cd frontend && npm install --legacy-peer-deps --silent)
fi

(
    cd frontend
    npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo "  ✅ 系統已啟動"
echo "============================================================"
echo ""
echo "  前端：     http://localhost:3000"
echo "  後端 API： http://localhost:8000"
echo "  API 文件： http://localhost:8000/docs"
echo "  登入帳號： admin / 1234"
echo ""
echo "  按 Ctrl+C 停止所有服務"
echo ""

# 等待任一子程序結束
wait
