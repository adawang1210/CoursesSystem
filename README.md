[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template)

# AI 教學計畫系統（AI Teaching Plan System）

一個整合 AI 診斷分析的教學互動平台，讓教師透過 LINE Bot 發布課後 Q&A 任務，收集學生作答後由 AI 自動聚類分析，探測學生的認知狀態與迷思概念。

## 目錄

- [專案概述](#專案概述)
- [技術棧](#技術棧)
- [專案結構](#專案結構)
- [環境需求](#環境需求)
- [安裝與設定](#安裝與設定)
- [環境變數](#環境變數)
- [啟動系統](#啟動系統)
- [生產環境建置](#生產環境建置)
- [資料庫](#資料庫)
- [API 端點文件](#api-端點文件)
- [常見問題與疑難排解](#常見問題與疑難排解)
- [相關文件](#相關文件)

---

## 專案概述

本系統為大學教師設計，核心流程如下：

1. 教師在後台建立課程，並發布「課後 Q&A 診斷任務」（含核心觀念與預期迷思）
2. 系統透過 LINE Bot 將任務推播給已綁定課程的學生
3. 學生在 LINE 中直接回覆作答，系統自動去識別化後儲存
4. 教師在後台批閱作答（通過 / 退回），並觸發 AI 聚類分析
5. AI 根據教師設定的核心觀念與預期迷思，將學生回答分群診斷
6. 教師查看診斷結果、匯出 CSV 報表進行教學研究

系統特色：
- 學生身份去識別化（SHA256 雜湊），保護隱私
- AI 診斷式聚類（非簡單對錯，而是分析認知狀態）
- LINE Bot 即時互動（限時 / 不限時任務、作答次數限制）
- 完整的 CSV 匯出功能（作答明細、Q&A 紀錄、統計報表、AI 分析）

---

## 技術棧

### 後端
| 技術 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 執行環境 |
| FastAPI | ≥0.115.0 | Web 框架 |
| Uvicorn | 0.24.0 | ASGI 伺服器 |
| Motor | 3.3.2 | MongoDB 非同步驅動 |
| PyMongo | 4.6.0 | MongoDB 驅動 |
| Pydantic | ≥2.9.0 | 資料驗證 |
| pydantic-settings | 2.1.0 | 環境變數管理 |
| python-jose | 3.3.0 | JWT 認證 |
| passlib + bcrypt | 1.7.4 / 4.1.1 | 密碼加密 |
| line-bot-sdk | 3.6.0 | LINE Messaging API |
| google-genai | ≥1.0.0 | Google Gemini AI SDK |
| pandas | ≥2.2.2 | CSV 匯出 |
| openpyxl | 3.1.2 | Excel 支援 |

### 前端
| 技術 | 版本 | 用途 |
|------|------|------|
| Next.js | ≥16.1.1 | React 框架 |
| React | 19.2.0 | UI 函式庫 |
| TypeScript | 5.x | 型別安全 |
| Tailwind CSS | 4.x | 樣式框架 |
| Radix UI | 各元件 | 無障礙 UI 元件 |
| Recharts | latest | 圖表視覺化 |
| Lucide React | 0.454.0 | 圖示 |
| next-themes | 0.4.6 | 深色模式 |
| React Hook Form + Zod | 7.x / 3.x | 表單驗證 |

### 資料庫
| 技術 | 版本 | 用途 |
|------|------|------|
| MongoDB | 4.4+ (建議 7.0) | 文件資料庫 |

### 外部服務
| 服務 | 用途 |
|------|------|
| Google Gemini API | AI 聚類分析、回覆草稿生成 |
| LINE Messaging API | 學生互動推播 |
| ngrok（開發用） | 本地 HTTPS 隧道 |

---

## 專案結構

```
CoursesSystem/
├── .github/workflows/                # CI/CD 自動化
│   ├── ci.yml                        #   持續整合（lint、build、test）
│   └── deploy.yml                    #   自動部署（SSH 到生產伺服器）
├── backend/                          # Python FastAPI 後端
│   ├── app/
│   │   ├── api/                      # API 路由層
│   │   │   ├── ai_integration.py     #   AI 聚類分析、草稿生成
│   │   │   ├── announcements.py      #   公告 CRUD
│   │   │   ├── courses.py            #   課程與班級 CRUD
│   │   │   ├── database.py           #   資料庫管理（概覽、結構分析）
│   │   │   ├── line_integration.py   #   LINE Webhook、統計、訊息
│   │   │   ├── qas.py               #   Q&A 任務 CRUD、學生回覆
│   │   │   ├── questions.py          #   學生作答 CRUD、批閱
│   │   │   └── reports.py            #   統計 JSON + CSV 匯出
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic 資料模型定義
│   │   ├── services/                 # 業務邏輯層
│   │   │   ├── ai_service.py         #   Google Gemini API 呼叫、聚類分析
│   │   │   ├── course_service.py     #   課程與班級服務
│   │   │   ├── export_service.py     #   CSV 匯出服務
│   │   │   ├── line_service.py       #   LINE 訊息處理、推播
│   │   │   ├── qa_service.py         #   Q&A 與公告服務
│   │   │   └── question_service.py   #   作答紀錄服務
│   │   ├── utils/
│   │   │   ├── datetime_helper.py    #   日期時間工具
│   │   │   └── security.py           #   密碼、JWT、去識別化
│   │   ├── config.py                 # 環境變數配置
│   │   ├── database.py               # MongoDB 連線管理
│   │   └── main.py                   # FastAPI 應用程式入口
│   ├── requirements.txt              # Python 相依套件
│   ├── check_db_clusters.py          # 除錯：檢查聚類資料
│   ├── check_line_data.py            # 除錯：檢查 LINE 訊息
│   ├── clear_test_line_data.py       # 工具：清除測試訊息
│   ├── create_test_data.py           # 工具：建立測試課程與提問
│   ├── create_test_line_messages.py  # 工具：建立測試 LINE 訊息
│   ├── hard_delete_questions.py      # 工具：永久刪除課程資料
│   ├── reset_clusters.py             # 工具：重置聚類結果
│   └── view_db.py                    # 工具：查看資料庫內容
│
├── frontend/                         # Next.js + TypeScript 前端
│   ├── app/
│   │   ├── layout.tsx                # 根版面（字型、主題、Auth）
│   │   ├── page.tsx                  # 首頁（重導至 /login）
│   │   ├── globals.css               # 全域樣式（Tailwind + 主題變數）
│   │   ├── login/page.tsx            # 登入頁（Mock: admin/1234）
│   │   └── dashboard/
│   │       ├── layout.tsx            # 後台版面（側邊欄 + Header）
│   │       ├── page.tsx              # 儀表板首頁
│   │       ├── courses/page.tsx      # 課程管理
│   │       ├── qa/page.tsx           # Q&A 任務管理（含批閱）
│   │       ├── clustering/page.tsx   # AI 聚類診斷結果
│   │       ├── announcements/page.tsx# 公告管理
│   │       ├── statistics/page.tsx   # 統計報表與 CSV 匯出
│   │       └── line-integration/     # LINE Bot 整合管理
│   ├── components/                   # 共用元件
│   │   ├── dashboard-header.tsx      # 頂部導覽列
│   │   ├── dashboard-sidebar.tsx     # 側邊選單
│   │   ├── theme-provider.tsx        # next-themes 封裝
│   │   ├── theme-wrapper.tsx         # 主題 Context 封裝
│   │   └── ui/                       # shadcn/ui 元件庫（57 個）
│   ├── contexts/
│   │   ├── auth-context.tsx          # 認證 Context（Mock）
│   │   └── theme-context.tsx         # 主題 Context（亮/暗）
│   ├── hooks/
│   │   ├── use-mobile.ts            # 行動裝置偵測
│   │   └── use-toast.ts             # Toast 通知
│   ├── lib/
│   │   ├── api-client.ts            # API 客戶端（fetch 封裝）
│   │   ├── utils.ts                 # cn() 工具函式
│   │   └── api/                     # 各模組 API 函式
│   │       ├── ai.ts                #   AI 聚類 API
│   │       ├── announcements.ts     #   公告 API
│   │       ├── courses.ts           #   課程 API
│   │       ├── database.ts          #   資料庫管理 API
│   │       ├── line.ts              #   LINE 整合 API
│   │       ├── qas.ts              #   Q&A API
│   │       ├── questions.ts         #   作答 API
│   │       ├── reports.ts           #   報表 API
│   │       └── index.ts             #   統一匯出
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.mjs
│   └── postcss.config.mjs
│
├── start_backend.sh                  # 後端啟動腳本
├── start_frontend.sh                 # 前端啟動腳本
├── ngrok.sh                          # ngrok 管理腳本
├── view_mongodb.sh                   # MongoDB 查看腳本
├── LINE_SETUP.md                     # LINE Bot 設定指南
├── DEPLOYMENT.md                     # 生產環境部署指南
└── README.md                         # 本文件
```

---

## 環境需求

| 軟體 | 最低版本 | 建議版本 |
|------|---------|---------|
| Python | 3.9 | 3.11+ |
| Node.js | 18.0 | 20+ |
| npm | 9.0 | 10+ |
| MongoDB | 4.4 | 7.0 |
| ngrok（開發用） | 任意 | 最新 |

---

## 安裝與設定

### 1. 安裝 MongoDB

macOS（Homebrew）：
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

Ubuntu：
```bash
sudo apt-get install -y mongodb
sudo systemctl start mongodb
```

Windows：從 [MongoDB 官方下載頁面](https://www.mongodb.com/try/download/community) 下載 MSI 安裝程式。

### 2. 安裝後端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 3. 安裝前端

由於本專案使用 React 19，部分套件的 peer dependency 宣告尚未更新，安裝時需加上 `--legacy-peer-deps` 旗標：

```bash
cd frontend
npm install --legacy-peer-deps
```

### 4. 設定環境變數

在 `backend/` 目錄下建立 `.env` 檔案（參見下方「環境變數」章節）。

---

## 環境變數

在 `backend/.env` 中設定以下變數：

```env
# ===== 資料庫 =====
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=courses_system

# ===== JWT 認證 =====
# 用於後端 API 的 JWT Token 簽發，請使用至少 32 字元的隨機字串
JWT_SECRET_KEY=<請替換為隨機生成的強密碼>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# ===== 去識別化 =====
# 用於 SHA256 雜湊 LINE User ID 的鹽值，請使用至少 32 字元的隨機字串
# 一旦設定後請勿更改，否則已有的 pseudonym 將無法對應
PSEUDONYM_SALT=<請替換為隨機生成的鹽值>

# ===== LINE Bot =====
# 從 LINE Developers Console 取得
LINE_CHANNEL_SECRET=<你的 Channel Secret>
LINE_CHANNEL_ACCESS_TOKEN=<你的 Channel Access Token>

# ===== AI 服務 =====
# 從 Google AI Studio 取得 API Key: https://aistudio.google.com/apikey
GEMINI_API_KEY=<你的 Gemini API Key>
GEMINI_MODEL=gemini-2.0-flash

# ===== API 伺服器 =====
API_HOST=0.0.0.0
API_PORT=8000

# ===== CORS =====
# 允許的前端來源，多個以逗號分隔
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

前端可選環境變數（在 `frontend/.env.local`）：
```env
# 後端 API 位址（預設 http://localhost:8000）
NEXT_PUBLIC_API_URL=http://localhost:8000
```

生成隨機密碼：
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 啟動系統

### 方式 A：使用啟動腳本

```bash
# 終端機 1 — 後端
./start_backend.sh

# 終端機 2 — 前端
./start_frontend.sh

# 終端機 3 — ngrok（如需 LINE Bot）
./ngrok.sh start
```

### 方式 B：手動啟動

```bash
# 終端機 1 — 後端
cd backend
source venv/bin/activate
python -m app.main

# 終端機 2 — 前端
cd frontend
npm run dev
```

### 存取位址

| 服務 | URL |
|------|-----|
| 前端 | http://localhost:3000 |
| 後端 API | http://localhost:8000 |
| Swagger API 文件 | http://localhost:8000/docs |
| ReDoc API 文件 | http://localhost:8000/redoc |
| 健康檢查 | http://localhost:8000/health |
| ngrok 控制台 | http://localhost:4040 |

登入帳號（Mock）：`admin` / `1234`

---

## 生產環境建置

### 後端

```bash
cd backend
source venv/bin/activate
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 前端

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
npm start          # 啟動 Next.js 生產伺服器（port 3000）
```

詳細部署方案（Docker、Systemd、Nginx、SSL）請參考 [DEPLOYMENT.md](./DEPLOYMENT.md)。

---

## Railway 部署

Railway 是最簡單的雲端部署方式，適合學生與小型課堂使用。

### 步驟

1. 在 [Railway](https://railway.com/) 建立帳號並連結此 GitHub repo
2. 建立後端服務（courses-api）：
   - New Service → GitHub Repo → 設定 Dockerfile Path 為 `Dockerfile`（專案根目錄）
   - Railway 會自動偵測並使用此 Dockerfile 建置
3. 建立前端服務（courses-frontend）：
   - New Service → GitHub Repo → 設定 Dockerfile Path 為 `frontend/Dockerfile.frontend`
4. 新增 MongoDB：
   - 使用 [MongoDB Atlas](https://www.mongodb.com/atlas) 免費方案（M0 Shared Cluster）
   - 或在 Railway 中新增 MongoDB Plugin
5. 在 Railway 的 Variables 頁面設定所有環境變數：

   | 變數名稱 | 說明 | 必填 |
   |---------|------|------|
   | `MONGODB_URI` | MongoDB 連線字串（Atlas 或 Railway Plugin） | ✅ |
   | `MONGODB_DB_NAME` | 資料庫名稱，例如 `courses_system` | ✅ |
   | `JWT_SECRET_KEY` | JWT 簽發密鑰（至少 32 字元隨機字串） | ✅ |
   | `PSEUDONYM_SALT` | 去識別化鹽值（至少 32 字元隨機字串） | ✅ |
   | `LINE_CHANNEL_SECRET` | LINE Bot Channel Secret | 選填 |
   | `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Access Token | 選填 |
   | `GEMINI_API_KEY` | Google Gemini API Key | 選填 |
   | `GEMINI_MODEL` | Gemini 模型名稱，預設 `gemini-2.0-flash` | 選填 |
   | `API_HOST` | `0.0.0.0` | 選填 |
   | `API_PORT` | `8000` | 選填 |
   | `CORS_ORIGINS` | 前端服務的 Railway URL | ✅ |

6. 在 LINE Developers Console 將 Webhook URL 設為後端服務的 Railway URL：
   - 格式：`https://<your-backend>.up.railway.app/line/webhook`
7. 將 `CORS_ORIGINS` 設為前端服務的 Railway URL：
   - 格式：`https://<your-frontend>.up.railway.app`

詳細說明請參考 [DEPLOYMENT.md](./DEPLOYMENT.md)。

---

## 資料庫

### MongoDB Collections

| Collection | 說明 |
|-----------|------|
| `courses` | 課程資料 |
| `classes` | 班級資料（隸屬於課程） |
| `questions` | 學生作答紀錄（去識別化） |
| `qas` | Q&A 任務（教師發布的診斷題目） |
| `announcements` | 課程公告 |
| `clusters` | AI 聚類主題（診斷分群結果） |
| `line_messages` | LINE 訊息紀錄 |
| `line_users` | LINE 使用者綁定資料（課程、學號） |
| `users` | 系統使用者（教師/助教） |

### 建立測試資料

```bash
cd backend
source venv/bin/activate

# 建立測試課程與提問
python create_test_data.py

# 建立測試 LINE 訊息
python create_test_line_messages.py
```

### 查看資料庫

```bash
# 使用 Python 工具
cd backend && source venv/bin/activate
python view_db.py                    # 概覽所有 Collection
python view_db.py questions 10       # 查看特定 Collection

# 使用 mongosh
./view_mongodb.sh
```

### 建議索引

```javascript
use courses_system

db.questions.createIndex({ "course_id": 1 })
db.questions.createIndex({ "cluster_id": 1 })
db.questions.createIndex({ "reply_to_qa_id": 1 })
db.questions.createIndex({ "pseudonym": 1 })
db.questions.createIndex({ "created_at": -1 })
db.qas.createIndex({ "course_id": 1 })
db.qas.createIndex({ "is_published": 1 })
db.clusters.createIndex({ "course_id": 1, "qa_id": 1 })
db.line_messages.createIndex({ "user_id": 1 })
db.line_messages.createIndex({ "created_at": -1 })
db.line_users.createIndex({ "user_id": 1 }, { unique: true })
db.courses.createIndex({ "course_code": 1, "semester": 1 })
```

---

## API 端點文件

啟動後端後可存取完整互動式文件：http://localhost:8000/docs

以下為所有端點摘要：

### 根路徑
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | API 歡迎訊息 |
| GET | `/health` | 健康檢查（含資料庫狀態） |

### 課程管理 `/courses`
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/courses/` | 建立新課程 |
| GET | `/courses/` | 取得課程列表（可篩選 semester、is_active） |
| GET | `/courses/{course_id}` | 取得課程詳情 |
| PATCH | `/courses/{course_id}` | 更新課程 |
| DELETE | `/courses/{course_id}` | 刪除課程（軟刪除，級聯處理） |
| POST | `/courses/sync` | 從外部系統批次同步課程 |
| POST | `/courses/{course_id}/classes` | 建立班級 |
| GET | `/courses/{course_id}/classes` | 取得課程的所有班級 |
| GET | `/courses/{course_id}/classes/{class_id}` | 取得班級詳情 |
| PATCH | `/courses/{course_id}/classes/{class_id}` | 更新班級 |
| DELETE | `/courses/{course_id}/classes/{class_id}` | 刪除班級（軟刪除） |

### Q&A 任務管理 `/qas`
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/qas/?created_by=xxx` | 建立 Q&A（發布時自動推播 LINE） |
| GET | `/qas/` | 取得 Q&A 列表（可篩選 course_id、is_published） |
| GET | `/qas/{qa_id}` | 取得 Q&A 詳情 |
| GET | `/qas/{qa_id}/replies` | 取得該 Q&A 的所有學生回覆 |
| PATCH | `/qas/{qa_id}` | 更新 Q&A |
| POST | `/qas/{qa_id}/stop` | 提前結束限時 Q&A |
| POST | `/qas/{qa_id}/link-questions` | 連結提問至 Q&A |
| DELETE | `/qas/{qa_id}` | 刪除 Q&A（硬刪除） |
| GET | `/qas/search/?course_id=xxx&keyword=xxx` | 搜尋 Q&A |

### 學生作答管理 `/questions`
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/questions/` | 建立作答（LINE Bot 調用，自動去識別化） |
| GET | `/questions/` | 取得作答列表（可篩選 course_id、class_id） |
| GET | `/questions/{question_id}` | 取得作答詳情 |
| PATCH | `/questions/{question_id}/review` | 更新單筆批閱狀態與評語 |
| POST | `/questions/batch-review` | 批量更新批閱狀態 |
| GET | `/questions/cluster/{cluster_id}?course_id=xxx` | 取得同聚類的作答 |
| DELETE | `/questions/{question_id}` | 刪除作答（硬刪除） |

### AI 整合 `/ai`
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/ai/analysis/batch` | 批次寫入 AI 分析結果 |
| POST | `/ai/analysis/single` | 單筆寫入 AI 分析結果 |
| POST | `/ai/questions/{question_id}/draft` | 生成 AI 回覆草稿（背景任務） |
| POST | `/ai/clusters/generate` | 執行 AI 聚類分析（Q&A 批閱模式 / 一般模式） |
| GET | `/ai/clusters/{course_id}?qa_id=xxx` | 取得聚類主題列表 |
| PATCH | `/ai/clusters/{cluster_id}` | 更新聚類（改名、鎖定） |
| POST | `/ai/clusters/manual` | 手動新增聚類主題 |
| DELETE | `/ai/clusters/{cluster_id}` | 刪除聚類主題 |

> 注意：`GET /ai/questions/pending` 端點雖已在路由中定義，但後端服務層尚未實作 `get_pending_questions_for_ai` 方法，呼叫會回傳 500 錯誤。如需使用，請先在 `backend/app/services/question_service.py` 中補上該方法。

### 公告管理 `/announcements`
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/announcements/` | 建立公告（發布時自動推播 LINE） |
| GET | `/announcements/` | 取得公告列表 |
| GET | `/announcements/{id}` | 取得公告詳情 |
| PATCH | `/announcements/{id}` | 更新公告（草稿轉發布時觸發推播） |
| POST | `/announcements/{id}/send-to-line?line_message_id=xxx` | 標記已發送至 LINE |
| DELETE | `/announcements/{id}` | 刪除公告（硬刪除） |

### 報表與統計 `/reports`
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/reports/statistics?course_id=xxx` | 取得統計摘要 JSON（圖表用） |
| GET | `/reports/clusters/summary?course_id=xxx` | 取得聚類摘要 JSON（圖表用） |
| GET | `/reports/export/questions?course_id=xxx` | 匯出作答明細 CSV |
| GET | `/reports/export/clusters?course_id=xxx` | 匯出 AI 聚類分析 CSV |
| GET | `/reports/export/qas?course_id=xxx` | 匯出 Q&A 紀錄 CSV |
| GET | `/reports/export/statistics?course_id=xxx` | 匯出統計資料 CSV |

### LINE Bot 整合 `/line`
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/line/config` | 取得 LINE Bot 配置狀態 |
| GET | `/line/webhook-url` | 取得 Webhook URL |
| POST | `/line/webhook` | LINE Webhook 接收器 |
| GET | `/line/stats` | 取得 LINE Bot 統計 |
| GET | `/line/users` | 取得 LINE 使用者列表 |
| GET | `/line/messages` | 取得 LINE 訊息歷史 |
| GET | `/line/message-stats?days=7` | 取得訊息統計資料 |
| POST | `/line/test-connection` | 測試 LINE Bot 連接 |

### 資料庫管理 `/database`
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/database/overview` | 取得資料庫概覽 |
| GET | `/database/collections/{name}` | 取得集合資料（分頁） |
| GET | `/database/collections/{name}/sample` | 取得集合隨機樣本 |
| GET | `/database/collections/{name}/schema` | 分析集合欄位結構 |

---

## 常見問題與疑難排解

### MongoDB 連線失敗
- 確認 MongoDB 服務正在運行：`brew services list`（macOS）或 `sudo systemctl status mongod`（Linux）
- 確認 `MONGODB_URI` 設定正確
- 確認防火牆未阻擋 27017 port

### 前端無法連接後端
- 確認後端正在運行：`curl http://localhost:8000/health`
- 確認 `CORS_ORIGINS` 包含前端 URL（`http://localhost:3000`）
- 檢查瀏覽器 Console 是否有 CORS 錯誤

### LINE Webhook 驗證失敗
- 確認後端正在運行
- 確認 ngrok 正在運行且 URL 未過期：`./ngrok.sh url`
- 確認 `.env` 中 `LINE_CHANNEL_SECRET` 和 `LINE_CHANNEL_ACCESS_TOKEN` 正確
- Webhook URL 格式：`https://xxxx.ngrok-free.app/line/webhook`

### AI 聚類分析無結果
- 確認 `.env` 中 `GEMINI_API_KEY` 已設定且有效
- 可從 [Google AI Studio](https://aistudio.google.com/apikey) 免費取得 API Key
- 確認有已通過批閱（approved）的學生作答可供分析
- 查看後端 Console 是否有 Gemini API 呼叫錯誤

### 前端登入後白畫面
- 使用 Mock 帳號：`admin` / `1234`
- 清除瀏覽器 localStorage 後重試

### CSV 匯出亂碼
- 匯出的 CSV 使用 UTF-8 BOM 編碼
- 在 Excel 中開啟時選擇「UTF-8」編碼
- 或使用 Google Sheets 匯入

### npm install 失敗（peer dependency 衝突）
- 本專案使用 React 19，部分套件（如 `vaul`）的 peer dependency 尚未更新
- 解決方式：使用 `npm install --legacy-peer-deps`
- 所有 shell 腳本已內建此旗標

---

## 相關文件

- [LINE_SETUP.md](./LINE_SETUP.md) — LINE Bot 與 ngrok 完整設定指南
- [DEPLOYMENT.md](./DEPLOYMENT.md) — 生產環境部署指南（含 GitHub Actions CI/CD 設定）
- Swagger API 文件 — http://localhost:8000/docs
- ReDoc API 文件 — http://localhost:8000/redoc

---

## 授權

本專案採用 MIT 授權條款。
