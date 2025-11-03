#!/bin/bash

# ngrok 管理腳本
# 用於啟動 ngrok 或查看當前 ngrok URL

show_usage() {
    echo "用法: $0 [start|url|status]"
    echo ""
    echo "指令："
    echo "  start   - 啟動 ngrok 隧道服務"
    echo "  url     - 獲取並顯示當前的 ngrok URL"
    echo "  status  - 檢查 ngrok 運行狀態"
    echo ""
    echo "範例："
    echo "  $0 start   # 啟動 ngrok"
    echo "  $0 url     # 查看 URL"
    echo ""
}

start_ngrok() {
    echo "[啟動] 啟動 ngrok 隧道服務..."
    echo "將本地 port 8000 映射到公開的 HTTPS URL"
    echo ""
    
    # 啟動 ngrok
    ngrok http 8000 --log=stdout --log-format=logfmt
    
    # 注意：
    # 1. ngrok 會生成一個臨時的 HTTPS URL
    # 2. 前往 http://localhost:4040 查看 ngrok 控制台
    # 3. 使用生成的 HTTPS URL 配置 LINE Webhook
    # 4. 每次重啟 ngrok，URL 會改變（除非使用付費版的固定 domain）
}

get_ngrok_url() {
    echo "[檢查] 正在檢查 ngrok 狀態..."
    echo ""
    
    # 檢查 ngrok 是否正在運行
    if ! lsof -i:4040 > /dev/null 2>&1; then
        echo "[錯誤] ngrok 未運行"
        echo ""
        echo "請先執行以下命令啟動 ngrok："
        echo "  $0 start"
        echo ""
        echo "或者在背景執行："
        echo "  ngrok http 8000 > ngrok.log 2>&1 &"
        exit 1
    fi
    
    # 獲取 ngrok URL
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
    
    if [ -z "$NGROK_URL" ] || [ "$NGROK_URL" = "null" ]; then
        echo "[錯誤] 無法獲取 ngrok URL"
        exit 1
    fi
    
    echo "[成功] ngrok 正在運行"
    echo ""
    echo "HTTPS URL (用於 LINE Webhook):"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$NGROK_URL/line/webhook"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "ngrok 控制台: http://localhost:4040"
    echo ""
    echo "設定步驟："
    echo "1. 複製上方的 HTTPS URL"
    echo "2. 前往 LINE Developers Console"
    echo "3. 選擇您的 Messaging API Channel"
    echo "4. 在 Webhook settings 中貼上此 URL"
    echo "5. 啟用 Use webhook 並點擊 Verify"
    echo ""
}

check_status() {
    if lsof -i:4040 > /dev/null 2>&1; then
        echo "[狀態] ngrok 正在運行"
        echo "控制台: http://localhost:4040"
        return 0
    else
        echo "[狀態] ngrok 未運行"
        return 1
    fi
}

# 主程式邏輯
case "$1" in
    start)
        start_ngrok
        ;;
    url)
        get_ngrok_url
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac

