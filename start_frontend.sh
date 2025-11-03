#!/bin/bash
# AI 教學計畫系統 - 前端啟動腳本

echo "啟動 AI 教學計畫系統前端..."

# 進入前端目錄
cd frontend

# 檢查 node_modules
if [ ! -d "node_modules" ]; then
    echo "[資訊] 安裝前端相依套件..."
    npm install
fi

# 啟動前端服務
echo "[啟動] 前端服務啟動中..."
echo "前端網址：http://localhost:3000"
echo ""

npm run dev

