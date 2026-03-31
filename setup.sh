#!/bin/bash
# ============================================================
# AI 教學計畫系統 — 完整環境設定腳本
# 從零開始安裝所有相依套件並建立環境
# ============================================================

set -e

echo "============================================================"
echo "  AI 教學計畫系統 — 環境設定"
echo "============================================================"
echo ""

# ------ 檢查 Python ------
echo "[檢查] Python 版本..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo "  ✓ $PYTHON_VERSION"
else
    echo "  ✗ 找不到 python3，請先安裝 Python 3.9+"
    exit 1
fi

# ------ 檢查 Node.js ------
echo "[檢查] Node.js 版本..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo "  ✓ Node.js $NODE_VERSION"
else
    echo "  ✗ 找不到 node，請先安裝 Node.js 18+"
    exit 1
fi

# ------ 檢查 npm ------
echo "[檢查] npm 版本..."
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version 2>&1)
    echo "  ✓ npm $NPM_VERSION"
else
    echo "  ✗ 找不到 npm"
    exit 1
fi

# ------ 檢查 MongoDB ------
echo "[檢查] MongoDB..."
if command -v mongod &> /dev/null; then
    echo "  ✓ MongoDB 已安裝"
elif command -v mongosh &> /dev/null; then
    echo "  ✓ mongosh 已安裝（請確認 mongod 服務正在運行）"
else
    echo "  ⚠ 找不到 MongoDB，請確認已安裝並啟動 MongoDB 服務"
    echo "    macOS: brew tap mongodb/brew && brew install mongodb-community@7.0"
    echo "    Ubuntu: sudo apt-get install -y mongodb"
fi

echo ""

# ------ 設定後端 ------
echo "============================================================"
echo "[後端] 設定 Python 虛擬環境與安裝套件..."
echo "============================================================"

if [ ! -d "backend/venv" ]; then
    echo "  建立虛擬環境..."
    python3 -m venv backend/venv
fi

echo "  啟動虛擬環境並安裝套件..."
source backend/venv/bin/activate
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
deactivate

echo "  ✓ 後端套件安裝完成"

# ------ 設定後端 .env ------
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "[後端] 建立 .env 檔案..."
    
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    PSEUDONYM_SALT=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    cat > backend/.env << EOF
# ===== 資料庫 =====
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=courses_system

# ===== JWT 認證 =====
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# ===== 去識別化 =====
PSEUDONYM_SALT=${PSEUDONYM_SALT}

# ===== LINE Bot（請替換為你的值） =====
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=

# ===== Google Gemini AI（請替換為你的值） =====
# 從 https://aistudio.google.com/apikey 取得
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# ===== API 伺服器 =====
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
EOF

    echo "  ✓ 已建立 backend/.env（JWT_SECRET_KEY 和 PSEUDONYM_SALT 已自動生成）"
    echo "  ⚠ 請手動填入 LINE_CHANNEL_SECRET、LINE_CHANNEL_ACCESS_TOKEN、GEMINI_API_KEY"
else
    echo "  ✓ backend/.env 已存在，跳過"
fi

echo ""

# ------ 設定前端 ------
echo "============================================================"
echo "[前端] 安裝 Node.js 套件..."
echo "============================================================"

cd frontend
npm install --legacy-peer-deps --silent
cd ..

echo "  ✓ 前端套件安裝完成"

echo ""

# ------ 設定腳本權限 ------
echo "[權限] 設定腳本執行權限..."
chmod +x start_backend.sh start_frontend.sh ngrok.sh view_mongodb.sh setup.sh start.sh build.sh 2>/dev/null || true
echo "  ✓ 完成"

echo ""
echo "============================================================"
echo "  ✅ 環境設定完成"
echo "============================================================"
echo ""
echo "下一步："
echo "  1. 編輯 backend/.env 填入 LINE Bot 和 AI API 金鑰"
echo "  2. 確認 MongoDB 服務正在運行"
echo "  3. 執行 ./start.sh 啟動前後端"
echo "  4. 開啟 http://localhost:3000 使用系統"
echo "     登入帳號：admin / 1234"
echo ""
