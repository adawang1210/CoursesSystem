# 部署指南

本指南說明如何將 AI 教學計畫系統部署到生產環境。

## 目錄

1. [開發環境設定](#開發環境設定)
2. [生產環境部署](#生產環境部署)
3. [MongoDB 設定](#mongodb-設定)
4. [疑難排解](#疑難排解)

---

## 開發環境設定

### 系統需求

- **作業系統**：Windows 10+, macOS 10.15+, Ubuntu 20.04+
- **Python**：3.9 或以上
- **Node.js**：18.0 或以上
- **MongoDB**：4.4 或以上

### 快速啟動

詳細的開發環境設定請參考主 `README.md` 文檔。

---

## 生產環境部署

### 1. 環境變數設定

在伺服器上建立 `.env` 檔案：

```env
# 資料庫配置
MONGODB_URI=mongodb://username:password@mongodb-server:27017
MONGODB_DB_NAME=courses_system_prod

# JWT 配置（請使用強密碼）
JWT_SECRET_KEY=請更換為隨機生成的強密碼至少32字元
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 去識別化配置（請使用強密碼）
PSEUDONYM_SALT=請更換為隨機生成的鹽值至少32字元

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com

# Line Bot 配置
LINE_CHANNEL_SECRET=your-production-line-channel-secret
LINE_CHANNEL_ACCESS_TOKEN=your-production-line-access-token

# AI 服務配置
AI_SERVICE_URL=http://ai-service:8001
AI_SERVICE_API_KEY=your-ai-service-api-key
```

**生成隨機密碼：**

```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. 後端部署

#### 選項 A：使用 Docker（推薦）

**建立 Dockerfile：**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY .env .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**建立 docker-compose.yml：**

```yaml
version: "3.8"

services:
  mongodb:
    image: mongo:7.0
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: your-mongo-password
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"

  backend:
    build: .
    restart: always
    ports:
      - "8000:8000"
    depends_on:
      - mongodb
    environment:
      MONGODB_URI: mongodb://admin:your-mongo-password@mongodb:27017

volumes:
  mongodb_data:
```

**啟動服務：**

```bash
docker-compose up -d
```

#### 選項 B：使用 Systemd + Gunicorn

**安裝 Gunicorn：**

```bash
pip install gunicorn uvicorn[standard]
```

**建立 Systemd 服務** (`/etc/systemd/system/courses-api.service`)

```ini
[Unit]
Description=AI Courses System API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/courses-system/backend
Environment="PATH=/var/www/courses-system/backend/venv/bin"
ExecStart=/var/www/courses-system/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

**啟動服務：**

```bash
sudo systemctl enable courses-api
sudo systemctl start courses-api
sudo systemctl status courses-api
```

**Nginx 配置** (`/etc/nginx/sites-available/courses-api`)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**啟用站點：**

```bash
sudo ln -s /etc/nginx/sites-available/courses-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. 前端部署

#### 建置生產版本

```bash
cd frontend
npm install
npm run build
```

#### 選項 A：使用 Nginx 部署（靜態匯出）

首先，在 `next.config.mjs` 中啟用靜態匯出：

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
};
export default nextConfig;
```

然後建置：

```bash
npm run build
# 輸出到 out/ 目錄
```

**Nginx 配置** (`/etc/nginx/sites-available/courses-frontend`)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    root /var/www/courses-system/frontend/out;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### 選項 B：使用 PM2 部署（SSR）

```bash
# 安裝 PM2
npm install -g pm2

# 啟動 Next.js
cd /var/www/courses-system/frontend
pm2 start npm --name "courses-frontend" -- start
pm2 save
pm2 startup
```

### 4. SSL/HTTPS 設定（使用 Let's Encrypt）

```bash
# 安裝 Certbot
sudo apt install certbot python3-certbot-nginx

# 取得 SSL 憑證
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Certbot 會自動配置 Nginx 並設定自動更新
```

---

## MongoDB 設定

### 1. 建立資料庫使用者

```bash
mongosh

use courses_system

db.createUser({
  user: "courses_user",
  pwd: "strong_password_here",
  roles: [
    { role: "readWrite", db: "courses_system" }
  ]
})
```

### 2. 建立索引（提升查詢效能）

```javascript
// 連線至資料庫
use courses_system

// 提問集合索引
db.questions.createIndex({ "course_id": 1 })
db.questions.createIndex({ "class_id": 1 })
db.questions.createIndex({ "status": 1 })
db.questions.createIndex({ "cluster_id": 1 })
db.questions.createIndex({ "created_at": -1 })
db.questions.createIndex({ "pseudonym": 1 })

// Q&A 集合索引
db.qas.createIndex({ "course_id": 1 })
db.qas.createIndex({ "is_published": 1 })
db.qas.createIndex({ "question": "text", "answer": "text" })

// 課程集合索引
db.courses.createIndex({ "course_code": 1, "semester": 1 }, { unique: true })
db.courses.createIndex({ "is_active": 1 })
```

### 3. 啟用認證

編輯 `/etc/mongod.conf`：

```yaml
security:
  authorization: enabled
```

重啟 MongoDB：

```bash
sudo systemctl restart mongod
```

### 4. 資料備份

**備份：**

```bash
mongodump --db courses_system --out /backup/mongodb/$(date +%Y%m%d)
```

**還原：**

```bash
mongorestore --db courses_system /backup/mongodb/20231103/courses_system/
```

**自動備份（crontab）：**

```bash
# 編輯 crontab
crontab -e

# 每天凌晨 2 點備份
0 2 * * * mongodump --db courses_system --out /backup/mongodb/$(date +\%Y\%m\%d)

# 刪除 30 天前的備份
0 3 * * * find /backup/mongodb -type d -mtime +30 -exec rm -rf {} \;
```

---

## LINE Bot 生產環境設定

在生產環境中，**不應使用 ngrok**。請：

1. **使用固定的 domain 和 HTTPS**

   - 例如：`https://api.yourdomain.com/line/webhook`

2. **在 LINE Developers Console 設定 Webhook URL**

   - 使用您的正式 domain

3. **確保環境變數正確設定**
   - Channel Secret
   - Access Token

詳細的 LINE Bot 設定請參考 `LINE_SETUP.md`（僅 ngrok 部分不適用於生產環境）。

---

## 疑難排解

### 常見問題

#### 1. MongoDB 連線失敗

**檢查事項：**

- MongoDB 服務是否正在運行：`sudo systemctl status mongod`
- MONGODB_URI 是否正確
- 網路防火牆設定
- MongoDB 認證憑證

#### 2. CORS 錯誤

在 `.env` 中正確設定 CORS_ORIGINS：

```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

#### 3. JWT 認證失敗

確認 JWT_SECRET_KEY 在所有服務中一致，且已重啟服務。

#### 4. 前端無法連接後端

檢查：

- 後端服務是否運行
- Nginx 配置是否正確
- CORS 設定是否包含前端 domain
- 防火牆規則

### 查看日誌

**後端日誌（Systemd）：**

```bash
sudo journalctl -u courses-api -f
```

**後端日誌（Docker）：**

```bash
docker-compose logs -f backend
```

**Nginx 日誌：**

```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

**MongoDB 日誌：**

```bash
sudo tail -f /var/log/mongodb/mongod.log
```

---

## 效能優化

### 1. 資料庫優化

- 為常用查詢欄位建立索引
- 使用連線池
- 定期清理舊資料

### 2. 快取機制

考慮使用 Redis 快取常用資料：

```python
# 範例：快取課程列表
from redis import Redis
redis_client = Redis(host='localhost', port=6379)

# 設定快取
redis_client.setex('courses_list', 3600, json.dumps(courses))

# 讀取快取
cached = redis_client.get('courses_list')
```

### 3. CDN

使用 CDN 加速靜態檔案：

- 圖片
- CSS/JS 檔案
- 公開資源

### 4. 負載平衡

使用 Nginx 負載平衡多個後端實例：

```nginx
upstream backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

---

## 安全性檢查清單

部署前請確認：

- [ ] 更換所有預設密碼和密鑰
- [ ] 啟用 HTTPS（SSL/TLS）
- [ ] 設定強密碼原則
- [ ] 定期更新相依套件
- [ ] 啟用資料庫認證
- [ ] 設定防火牆規則
- [ ] 實作 API 速率限制
- [ ] 定期備份資料
- [ ] 監控異常登入
- [ ] 記錄審計日誌
- [ ] 限制 CORS 來源
- [ ] 隱藏詳細錯誤訊息（生產環境）

---

## 監控與維護

### 1. 健康檢查

設定監控工具定期檢查：

- 後端健康端點：`https://api.yourdomain.com/health`
- 資料庫連線狀態
- 磁碟空間

### 2. 日誌管理

- 使用 ELK Stack 或類似工具集中管理日誌
- 設定日誌輪替（log rotation）
- 監控錯誤率

### 3. 效能監控

使用工具如：

- New Relic
- Datadog
- Prometheus + Grafana

### 4. 自動化部署

考慮使用 CI/CD 工具：

- GitHub Actions
- GitLab CI
- Jenkins

---

## 雲端平台部署

### AWS

- **EC2**：虛擬機器
- **RDS**：託管 MongoDB（DocumentDB）
- **S3**：檔案儲存
- **CloudFront**：CDN
- **Route 53**：DNS

### Google Cloud Platform

- **Compute Engine**：虛擬機器
- **Cloud Run**：容器化部署
- **Cloud Storage**：檔案儲存
- **Cloud CDN**：CDN

### Azure

- **Virtual Machines**：虛擬機器
- **Cosmos DB**：MongoDB API
- **Blob Storage**：檔案儲存
- **Azure CDN**：CDN

### Heroku（簡易部署）

```bash
# 安裝 Heroku CLI
brew install heroku/brew/heroku

# 登入
heroku login

# 建立應用程式
heroku create courses-system

# 部署
git push heroku main

# 設定環境變數
heroku config:set JWT_SECRET_KEY=your-secret-key
```

---

## 參考資源

- [FastAPI 部署文檔](https://fastapi.tiangolo.com/deployment/)
- [Next.js 部署文檔](https://nextjs.org/docs/deployment)
- [MongoDB 安全性最佳實踐](https://docs.mongodb.com/manual/security/)
- [Nginx 配置指南](https://nginx.org/en/docs/)
- [Let's Encrypt 文檔](https://letsencrypt.org/docs/)

---
