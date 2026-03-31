#!/bin/bash
# ============================================================
# AI 教學計畫系統 — 前端啟動腳本
# 自動安裝套件後啟動 Next.js 開發伺服器
# ============================================================

set -e

echo "============================================================"
echo "  啟動 AI 教學計畫系統前端"
echo "============================================================"
echo ""

# 檢查 Node.js
if ! command -v node &> /dev/null; then
    echo "[錯誤] 找不到 node，請先安裝 Node.js 18+"
    exit 1
fi

# 進入前端目錄
cd frontend

# 安裝套件（如 node_modules 不存在）
if [ ! -d "node_modules" ]; then
    echo "[設定] 安裝前端相依套件..."
    npm install --legacy-peer-deps
fi

echo ""
echo "[啟動] 前端服務啟動中..."
echo "  前端網址：http://localhost:3000"
echo "  登入帳號：admin / 1234"
echo ""

# 啟動 Next.js 開發伺服器
npm run dev
