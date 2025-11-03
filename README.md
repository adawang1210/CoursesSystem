# AI 教學計畫系統

一個整合 AI/NLP 技術的教學提問管理系統，提供提問去識別化、AI 聚類分析、Q&A 管理與統計報表等功能。

## 專案架構

```
CoursesSystem/
├── backend/              # Python FastAPI 後端
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── models/      # 資料模型
│   │   ├── services/    # 業務邏輯
│   │   ├── utils/       # 工具函式
│   │   ├── config.py    # 配置管理
│   │   ├── database.py  # 資料庫連線
│   │   └── main.py      # 應用程式入口
│   ├── requirements.txt
│   └── .env             # 環境變數（請勿提交至 Git）
│
├── frontend/            # Next.js + TypeScript 前端
│   ├── app/            # 應用程式路由與頁面
│   │   ├── dashboard/  # 後台管理頁面
│   │   ├── login/      # 登入頁面
│   │   └── layout.tsx  # 版面配置
│   ├── components/     # UI 組件
│   ├── contexts/       # React Context
│   ├── lib/            # API 客戶端與工具
│   │   ├── api/        # API 服務層
│   │   └── api-client.ts
│   └── package.json
│
└── README.md
```

## 功能特色

### 階段一：資料倉儲層與核心 API

- **MongoDB 資料庫設計**：課程、班級、提問、Q&A、公告等核心資料模型
- **資料去識別化**：使用 SHA256 雜湊處理 Line User ID，確保隱私保護
- **CRUD API**：完整的增刪改查接口
- **課程同步機制**：支援外部系統資料同步

### 階段二：服務與應用層業務邏輯

- **提問狀態機**：PENDING → APPROVED/REJECTED/DELETED/WITHDRAWN
- **AI 資料串接**：
  - 輸入：提供去識別化提問供 AI/NLP 分析
  - 輸出：接收 AI 聚類結果與難度評分
- **Q&A 管理**：問題合併、內容編輯、發布控制
- **公告系統**：公告建立、編輯與 Line Bot 整合

### 階段三：Web 後台介面

- **儀表板**：即時統計與最近提問概覽
- **課程管理**：課程與班級的建立、編輯、刪除
- **提問審核**：
  - 批次同意/拒絕
  - AI 聚類檢視
  - 合併提問至 Q&A
- **Q&A 編輯器**：富文本編輯、標籤管理、發布控制
- **公告管理**：公告建立與 Line 發送
- **統計報表**：視覺化圖表與 CSV 匯出

### 階段四：資料匯出與驗證

- **CSV 匯出**：
  - 提問資料（去識別化）
  - Q&A 內容
  - 統計報表
- **系統整合測試**

## 技術棧

### 後端

- **框架**：FastAPI 0.104.1
- **資料庫**：MongoDB (Motor 非同步驅動)
- **認證**：JWT (python-jose)
- **密碼加密**：Bcrypt
- **去識別化**：SHA256 雜湊
- **匯出**：Pandas (CSV)

### 前端

- **框架**：Next.js 16 + React 19 + TypeScript
- **UI 庫**：Radix UI + Tailwind CSS
- **表單管理**：React Hook Form + Zod
- **圖表**：Recharts
- **主題管理**：next-themes
- **建置工具**：Next.js

## 快速開始

### 1. 環境需求

- Python 3.9+
- Node.js 18+
- MongoDB 4.4+

### 2. 安裝 MongoDB

**macOS（使用 Homebrew）**

```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Windows**

**方式 A：使用 MSI 安裝程式（推薦）**

1. 前往 [MongoDB 官方下載頁面](https://www.mongodb.com/try/download/community)
2. 選擇 Windows 版本（建議選擇 `.msi` 格式）
3. 執行安裝程式，選擇 "Complete" 安裝
4. 安裝完成後，MongoDB 會自動啟動為 Windows 服務

**方式 B：使用 Chocolatey**

```powershell
choco install mongodb
```

安裝完成後，手動啟動 MongoDB 服務：

```powershell
# 以系統管理員身份執行 PowerShell
net start MongoDB
```

**Ubuntu**

```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
```

### 3. 設定環境變數

在 `backend/.env` 檔案中，**必須修改**以下項目：

```env
# 請更換為強密碼（至少 32 字元）
JWT_SECRET_KEY=請在此輸入隨機生成的強密碼
PSEUDONYM_SALT=請在此輸入另一組隨機密碼

# 資料庫配置（預設值通常可用）
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=courses_system

# Line Bot 配置
LINE_CHANNEL_SECRET=your-line-channel-secret
LINE_CHANNEL_ACCESS_TOKEN=your-line-channel-access-token
```

**生成隨機密碼：**

```bash
# macOS/Linux
openssl rand -hex 32
```

```powershell
# Windows PowerShell
[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

**或使用 Python（跨平台，推薦）：**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**或使用線上工具：**
可使用 [Random.org](https://www.random.org/strings/) 或其他密碼生成器生成至少 64 字元的隨機字串。

### 4. 啟動系統

**方式 A：使用啟動腳本（推薦）**

```bash
# 終端機 1 - 啟動後端
./start_backend.sh

# 終端機 2 - 啟動前端
./start_frontend.sh
```

**方式 B：手動啟動**

```bash
# 終端機 1 - 後端
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.main

# 終端機 2 - 前端
cd frontend
npm install
npm run dev
```

### 5. 訪問系統

- **前端**：http://localhost:3000
- **後端 API 文件**：http://localhost:8000/docs
- **健康檢查**：http://localhost:8000/health

## API 文件

啟動後端服務後，可訪問以下網址查看 API 文件：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 主要 API 端點

### 課程管理

- `GET /courses/` - 取得課程列表
- `POST /courses/` - 建立新課程
- `GET /courses/{id}` - 取得課程詳情
- `PATCH /courses/{id}` - 更新課程
- `DELETE /courses/{id}` - 刪除課程

### 提問管理

- `GET /questions/` - 取得提問列表
- `POST /questions/` - 建立新提問（Line Bot 調用）
- `PATCH /questions/{id}/status` - 更新提問狀態
- `POST /questions/merge` - 合併提問至 Q&A
- `GET /questions/statistics/` - 取得統計資料

### AI 整合

- `GET /ai/questions/pending` - 取得待分析的提問
- `POST /ai/analysis/batch` - 批次寫入 AI 分析結果
- `GET /ai/clusters/{course_id}` - 取得聚類摘要

### Q&A 管理

- `GET /qas/` - 取得 Q&A 列表
- `POST /qas/` - 建立新 Q&A
- `PATCH /qas/{id}` - 更新 Q&A
- `POST /qas/{id}/link-questions` - 連結提問至 Q&A
- `GET /qas/search/` - 搜尋 Q&A

### 報表匯出

- `GET /reports/export/questions` - 匯出提問 CSV
- `GET /reports/export/qas` - 匯出 Q&A CSV
- `GET /reports/export/statistics` - 匯出統計 CSV

## 隱私保護機制

### 去識別化流程

1. **接收提問**：Line Bot 收到提問時，包含原始 `line_user_id`
2. **雜湊處理**：使用 `generate_pseudonym()` 函式進行 SHA256 雜湊
3. **儲存資料**：僅儲存 `pseudonym`，原始 ID 不寫入資料庫
4. **AI 分析**：AI 服務僅接收去識別化後的資料
5. **匯出限制**：所有匯出的 CSV 檔案不包含原始 ID

```python
from app.utils.security import generate_pseudonym

# 去識別化處理
pseudonym = generate_pseudonym(line_user_id)
# 輸出：64 字元的 SHA256 雜湊值
```

## 使用流程

### 教師/助教端操作流程

1. **課程設定**

   - 登入後台管理系統
   - 建立或匯入課程資料
   - 設定班級與助教

2. **提問審核**

   - 查看待處理提問
   - 使用 AI 聚類檢視快速識別相似問題
   - 批次同意或個別審核
   - 將相似提問合併為 Q&A

3. **Q&A 管理**

   - 編輯問題與回答內容
   - 添加分類與標籤
   - 發布 Q&A 供學生查閱

4. **公告發布**

   - 建立課程公告
   - 選擇性發送至 Line 群組

5. **統計分析**
   - 查看提問統計數據
   - 匯出資料進行深度分析

### Line Bot 整合（選用）

系統預留 Line Bot 整合接口，可實現：

- 學生透過 Line 提問
- 系統自動回覆相關 Q&A
- 發送課程公告至 Line 群組

**快速設定：**

1. 取得 LINE Channel Secret 和 Access Token
2. 在 `backend/.env` 中設定
3. 啟動 ngrok：`./ngrok.sh`
4. 在 LINE Developers Console 設定 Webhook URL

詳細設定步驟請參考 `LINE_SETUP.md`。

## 資料庫 Schema

### Collections

- **courses**：課程資料
- **classes**：班級資料
- **questions**：提問資料（已去識別化）
- **qas**：Q&A 內容
- **announcements**：公告資料
- **users**：使用者（教師/助教）

詳細 Schema 定義請參考 `backend/app/models/schemas.py`

## 測試

```bash
# 後端測試
cd backend
pytest

# 前端測試
cd frontend
npm test
```

## 開發注意事項

1. **隱私保護**：絕對不要在程式碼中直接儲存或記錄原始 Line User ID
2. **環境變數**：敏感資訊（JWT Secret、Salt）必須使用環境變數
3. **API 認證**：生產環境必須啟用 JWT 認證機制
4. **CORS 設定**：依實際部署環境調整 CORS 允許的來源
5. **資料庫索引**：建議為常用查詢欄位建立索引（course_id、status、cluster_id 等）

## 部署建議

### 後端部署

```bash
# 使用 Gunicorn + Uvicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 前端部署

```bash
# 建置生產版本
npm run build

# 使用 nginx 或其他靜態檔案伺服器部署 dist 目錄
```

### MongoDB 建議

- 啟用認證機制
- 定期備份資料
- 為常用查詢建立索引

## 授權

本專案採用 MIT 授權條款。

## 相關文檔

- **LINE_SETUP.md** - LINE Bot 與 ngrok 完整設定指南
- **DEPLOYMENT.md** - 生產環境部署指南
- **API 文件** - http://localhost:8000/docs
