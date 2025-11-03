# LINE Bot 設定指南

本指南整合了 LINE Bot 與 ngrok 的完整設定流程。

## 目錄

1. [快速設定](#快速設定-5分鐘)
2. [ngrok 設定](#ngrok-設定)
3. [LINE Developers Console 設定](#line-developers-console-設定)
4. [測試與驗證](#測試與驗證)
5. [疑難排解](#疑難排解)

---

## 快速設定（5 分鐘）

### 步驟 1：啟動所有服務

```bash
# 終端機 1 - 啟動後端
./start_backend.sh

# 終端機 2 - 啟動前端
./start_frontend.sh

# 終端機 3 - 啟動 ngrok
./start_ngrok.sh
# 或背景執行：ngrok http 8000 > ngrok.log 2>&1 &
```

### 步驟 2：取得 Webhook URL

```bash
./get_ngrok_url.sh
```

複製輸出的 HTTPS URL，例如：

```
https://4727829a31c7.ngrok-free.app/line/webhook
```

### 步驟 3：設定 LINE Console

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 選擇您的 Messaging API Channel
3. 在 **Webhook settings** 中貼上 HTTPS URL
4. 啟用 **Use webhook**
5. 點擊 **Verify** 驗證連接（應顯示 ✅ Success）

### 步驟 4：測試

透過 LINE 向您的 Bot 發送訊息，Bot 應該會回覆。

---

## ngrok 設定

### 什麼是 ngrok？

ngrok 是一個安全的隧道服務，可以：

- 將本地開發服務器暴露到公網
- 自動提供 HTTPS 加密
- 解決 LINE Webhook 必須使用 HTTPS 的要求

### 為什麼需要 ngrok？

LINE Messaging API 的 Webhook 要求：

- ✅ 必須使用 HTTPS 協議
- ✅ 必須可以從公網訪問
- ❌ 無法使用 `http://localhost:8000`

### 安裝 ngrok

```bash
# macOS
brew install ngrok

# 或下載：https://ngrok.com/download
```

### 啟動 ngrok

**選項 A：前台運行（推薦用於測試）**

```bash
./start_ngrok.sh
```

**選項 B：背景運行**

```bash
ngrok http 8000 > ngrok.log 2>&1 &
```

### 獲取 HTTPS URL

```bash
./get_ngrok_url.sh
```

或手動獲取：

```bash
curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'
```

### ngrok 監控控制台

ngrok 提供了 Web 控制台來監控所有請求：

- 網址：http://localhost:4040
- 可以查看所有 HTTP 請求和響應
- 對調試 Webhook 非常有用

### 常用命令

```bash
# 查看 ngrok 狀態
lsof -i:4040

# 停止 ngrok
pkill -f ngrok

# 查看 ngrok 日誌
tail -f ngrok.log
```

### ⚠️ 重要提示

**URL 會改變**

- ngrok 免費版每次重啟都會生成新的 URL
- 如果重啟了 ngrok，需要：
  1. 執行 `./get_ngrok_url.sh` 獲取新 URL
  2. 更新 LINE Developers Console 中的 Webhook URL

**固定 URL（付費功能）**

如果需要固定的 URL，可以升級到 ngrok 付費方案：

```bash
ngrok http 8000 --domain=your-fixed-domain.ngrok-free.app
```

---

## LINE Developers Console 設定

### 1. 建立 LINE Bot

1. 前往 [LINE Developers Console](https://developers.line.biz/)
2. 建立新的 Provider（或使用現有的）
3. 建立新的 Messaging API Channel
4. 取得以下資訊：
   - **Channel Secret**
   - **Channel Access Token**（長期）

### 2. 設定環境變數

在專案根目錄的 `.env` 檔案中設定：

```env
# LINE Bot 配置
LINE_CHANNEL_SECRET=your-line-channel-secret
LINE_CHANNEL_ACCESS_TOKEN=your-line-channel-access-token
```

### 3. 設定 Webhook URL

1. 在 LINE Developers Console 中
2. 選擇您的 Channel
3. 點擊 **Messaging API** 標籤
4. 找到 **Webhook settings**
5. 輸入 ngrok 提供的 HTTPS URL（例如：`https://xxxxx.ngrok-free.app/line/webhook`）
6. 啟用 **Use webhook** 開關
7. 點擊 **Verify** 按鈕

**預期結果：** 驗證成功會顯示 ✅ Success

### 4. 其他設定（選用）

**關閉自動回覆訊息**

- 在 **Messaging API** 標籤中
- 關閉 **Auto-reply messages**
- 關閉 **Greeting messages**
- 這樣 Bot 才會使用您的程式邏輯回覆

**允許加入群組**

- 在 **Messaging API** 標籤中
- 啟用 **Allow bot to join group chats**

---

## 測試與驗證

### 方法 1：使用前端介面測試

1. 訪問：http://localhost:3000/dashboard/line-integration
2. 點擊「測試連接」按鈕
3. 應該顯示「LINE Bot 連接正常」

### 方法 2：使用終端測試

```bash
# 測試後端健康狀態
curl http://localhost:8000/health

# 測試 LINE 配置
curl -s http://localhost:8000/line/config | jq .

# 測試 Webhook URL（通過 ngrok）
curl https://your-ngrok-url.ngrok-free.app/line/webhook-url
```

### 方法 3：發送真實訊息

1. 使用手機開啟 LINE
2. 找到您的 Bot（可以掃描 QR Code）
3. 發送訊息，例如：「測試」或「老師好」
4. Bot 應該會回覆

### 查看結果

**在前端查看：**

1. 訪問：http://localhost:3000/dashboard/line-integration
2. 刷新頁面
3. 應該會看到：
   - 訊息趨勢統計
   - 使用者活動
   - 訊息對話記錄（已去識別化）

**在 ngrok 控制台查看：**

- 訪問：http://localhost:4040
- 可以看到所有從 LINE 發來的請求

**查看後端日誌：**

```bash
cd backend
tail -f backend.log
```

成功的日誌應該顯示：

```
[Webhook] 收到 webhook 請求
[Webhook] 簽章驗證成功
[Webhook] 事件處理成功
```

### 查看資料庫

```bash
cd backend
source venv/bin/activate
python view_db.py
```

查看 `line_messages` 集合是否有新的訊息記錄。

---

## 疑難排解

### 問題 1：ngrok 無法啟動

**錯誤：** `ERROR: [Errno 48] Address already in use`

**解決：**

```bash
# 停止舊的 ngrok 進程
pkill -f ngrok

# 重新啟動
./start_ngrok.sh
```

### 問題 2：無法獲取 ngrok URL

**錯誤：** `curl: (7) Failed to connect to localhost port 4040`

**解決：**

```bash
# 檢查 ngrok 是否正在運行
lsof -i:4040

# 如果沒有運行，啟動它
./start_ngrok.sh
```

### 問題 3：LINE Webhook 驗證失敗

**可能原因：**

1. 後端服務未運行
2. ngrok 已停止或 URL 已改變
3. LINE Channel Secret/Access Token 設定錯誤
4. Webhook URL 格式錯誤

**解決步驟：**

```bash
# 1. 確認後端正在運行
curl http://localhost:8000/health

# 2. 確認 ngrok 正在運行並獲取 URL
./get_ngrok_url.sh

# 3. 測試 Webhook 端點
curl https://your-ngrok-url.ngrok-free.app/line/webhook-url

# 4. 檢查後端環境變數
cd backend
source venv/bin/activate
python -c "from app.config import settings; print(f'Secret: {bool(settings.LINE_CHANNEL_SECRET)}, Token: {bool(settings.LINE_CHANNEL_ACCESS_TOKEN)}')"
```

### 問題 4：發送訊息沒有收到回覆

**檢查項目：**

1. **查看 ngrok 控制台：** http://localhost:4040

   - 確認 LINE 的請求有送達
   - 查看請求和回應的內容

2. **查看後端日誌：**

   ```bash
   cd backend
   tail -f backend.log
   ```

3. **確認 Webhook 設定：**
   - LINE Console 中 Webhook URL 正確
   - "Use webhook" 已啟用
   - 驗證狀態為成功

### 問題 5：前端還是顯示測試資料

**解決方法：**

1. **清除測試資料：**

   ```bash
   cd backend
   source venv/bin/activate
   python clear_test_line_data.py
   # 輸入 1 確認刪除
   ```

2. **透過 LINE 發送測試訊息**

3. **刷新瀏覽器頁面**（Cmd+R 或 F5）

4. **確認資料庫：**
   ```bash
   python check_line_data.py
   ```

### 問題 6：CORS 錯誤

**症狀：** 瀏覽器控制台顯示 CORS 相關錯誤

**解決：**
後端的 CORS 已經配置支援 `http://localhost:3000`。如果還是有問題，檢查 `.env` 中的 `CORS_ORIGINS` 設定。

---

## 進階配置

### 自訂 ngrok 配置文件

編輯 `~/.config/ngrok/ngrok.yml`：

```yaml
version: "2"
authtoken: your_auth_token_here
tunnels:
  courses-system:
    proto: http
    addr: 8000
    inspect: true
    bind_tls: true
```

啟動特定隧道：

```bash
ngrok start courses-system
```

### 使用 ngrok 代理

如果您的網絡需要代理：

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
ngrok http 8000
```

---

## 安全性注意事項

1. **不要分享 ngrok URL**

   - URL 直接連接到您的本地開發環境
   - 任何人都可以訪問

2. **僅用於開發測試**

   - 生產環境應使用正式的 HTTPS 服務器
   - 不要用於處理敏感資料

3. **定期更換 URL**

   - 免費版會自動更換，這反而是個優點
   - 減少 URL 被濫用的風險

4. **保護環境變數**
   - 不要將 Channel Secret 和 Access Token 提交到 Git
   - 使用 `.env` 檔案並加入 `.gitignore`

---

## 生產環境部署

在生產環境中，不應使用 ngrok。請：

1. **部署到有固定 domain 的伺服器**

   - AWS、GCP、Azure、Heroku 等

2. **設定 HTTPS**

   - 使用 Let's Encrypt 免費 SSL 憑證
   - 或雲端服務提供的 SSL

3. **設定固定的 Webhook URL**
   - 例如：`https://api.yourdomain.com/line/webhook`

詳細部署說明請參考 `DEPLOYMENT.md`

---

## 檢查清單

設定完成前，確認以下項目：

- [ ] 後端服務運行中（port 8000）
- [ ] 前端服務運行中（port 3000）
- [ ] ngrok 運行中（port 4040）
- [ ] 已取得 ngrok HTTPS URL
- [ ] `.env` 中 LINE Channel Secret 和 Access Token 已設定
- [ ] LINE Webhook URL 已設定並驗證成功
- [ ] 已透過 LINE 發送測試訊息
- [ ] Bot 有回覆訊息
- [ ] 前端頁面顯示訊息記錄

---

## 參考資源

- [LINE Messaging API 官方文檔](https://developers.line.biz/en/docs/messaging-api/)
- [ngrok 官方文檔](https://ngrok.com/docs)
- [FastAPI Webhook 處理](https://fastapi.tiangolo.com/advanced/webhooks/)

---

## 完成！

設定完成後，您的系統將：

-  接收真實的 LINE 訊息（通過 HTTPS Webhook）
-  自動儲存訊息到資料庫
-  在前端顯示訊息統計和對話記錄
-  使用者身份已去識別化保護隱私
-  支援即時互動和回覆


