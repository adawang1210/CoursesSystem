#!/usr/bin/env python3
"""
檢查 LINE 訊息資料狀態
幫助判斷是測試資料還是真實資料
"""
import asyncio
from datetime import datetime, timedelta
import sys
import os

# 添加 app 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import db


async def check_line_data():
    """檢查 LINE 訊息資料"""
    print("=" * 60)
    print("LINE 訊息資料狀態檢查")
    print("=" * 60)
    
    # 連接資料庫
    print("\n🔍 連接資料庫...")
    await db.connect_db()
    
    try:
        database = db.get_db()
        messages_collection = database["line_messages"]
        
        # 統計總數
        total_count = await messages_collection.count_documents({})
        print(f"\n📊 總訊息數：{total_count}")
        
        if total_count == 0:
            print("\n❌ 資料庫中沒有任何 LINE 訊息資料")
            print("\n💡 建議：")
            print("  1. 確認 ngrok 正在運行")
            print("  2. 確認 LINE Webhook URL 已正確設定")
            print("  3. 透過 LINE 向您的 Bot 發送測試訊息")
            print("\n或者：")
            print("  執行 'python create_test_line_messages.py' 建立測試資料")
            return
        
        # 統計訊息方向
        received_count = await messages_collection.count_documents({"direction": "received"})
        sent_count = await messages_collection.count_documents({"direction": "sent"})
        failed_count = await messages_collection.count_documents({"direction": "failed"})
        
        print(f"  • 收到的訊息：{received_count}")
        print(f"  • 發送的訊息：{sent_count}")
        print(f"  • 失敗的訊息：{failed_count}")
        
        # 統計唯一使用者
        unique_users = await messages_collection.distinct("user_id")
        print(f"\n👥 唯一使用者數：{len(unique_users)}")
        
        # 檢查是否為測試資料
        test_user_pattern = "U00000000000000000000000000000"
        test_users = [uid for uid in unique_users if uid.startswith(test_user_pattern)]
        
        if test_users:
            print(f"\n⚠️  偵測到 {len(test_users)} 個測試使用者")
            print(f"  測試使用者 ID 範例：{test_users[0]}")
            is_test_data = True
        else:
            print("\n✅ 沒有偵測到測試使用者 ID 模式")
            is_test_data = False
        
        # 顯示最新的幾則訊息
        print("\n📝 最新 5 則訊息：")
        print("-" * 60)
        
        async for msg in messages_collection.find().sort("created_at", -1).limit(5):
            created_at = msg.get('created_at')
            if isinstance(created_at, datetime):
                time_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = str(created_at)
            
            direction_icon = {
                "received": "📥",
                "sent": "📤",
                "failed": "❌"
            }.get(msg.get('direction', ''), "❓")
            
            print(f"{direction_icon} {time_str}")
            print(f"   使用者：{msg.get('pseudonym', 'N/A')}")
            print(f"   內容：{msg.get('content', '')[:50]}...")
            print()
        
        # 時間分佈分析
        print("-" * 60)
        print("\n📅 訊息時間分佈：")
        
        now = datetime.utcnow()
        today_count = await messages_collection.count_documents({
            "created_at": {"$gte": now.replace(hour=0, minute=0, second=0, microsecond=0)}
        })
        
        yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_count = await messages_collection.count_documents({
            "created_at": {"$gte": yesterday_start, "$lt": yesterday_end}
        })
        
        week_start = now - timedelta(days=7)
        week_count = await messages_collection.count_documents({
            "created_at": {"$gte": week_start}
        })
        
        print(f"  • 今天：{today_count} 則")
        print(f"  • 昨天：{yesterday_count} 則")
        print(f"  • 過去 7 天：{week_count} 則")
        
        # 判斷並給出建議
        print("\n" + "=" * 60)
        print("💡 分析結果與建議：")
        print("=" * 60)
        
        if is_test_data:
            print("\n⚠️  資料庫中包含測試資料")
            print("\n如果您想連接真實的 LINE Bot 資料：")
            print("\n步驟 1：清除測試資料")
            print("  執行：python clear_test_line_data.py")
            print("\n步驟 2：設定 LINE Webhook")
            print("  1. 執行：../get_ngrok_url.sh")
            print("  2. 將取得的 HTTPS URL 設定到 LINE Developers Console")
            print("  3. 驗證 Webhook 連接")
            print("\n步驟 3：發送測試訊息")
            print("  透過 LINE 向您的 Bot 發送訊息")
            print("\n步驟 4：查看前端頁面")
            print("  訪問：http://localhost:3000/dashboard/line-integration")
            print("\n📖 詳細指南：請參考 ../連接真實LINE_BOT指南.md")
        else:
            print("\n✅ 資料看起來像是真實的 LINE Bot 資料")
            print("\n您可以在前端查看：")
            print("  訪問：http://localhost:3000/dashboard/line-integration")
            print("\n如果頁面沒有顯示這些資料：")
            print("  1. 刷新瀏覽器頁面（Cmd+R 或 F5）")
            print("  2. 檢查瀏覽器控制台是否有錯誤")
            print("  3. 確認後端服務正在運行")
        
        # 顯示使用者列表
        if len(unique_users) <= 10:
            print(f"\n👥 使用者列表：")
            for user_id in unique_users:
                user_msg_count = await messages_collection.count_documents({"user_id": user_id})
                pseudonym = await messages_collection.find_one({"user_id": user_id})
                pseudonym_str = pseudonym.get('pseudonym', 'N/A') if pseudonym else 'N/A'
                print(f"  • {pseudonym_str}：{user_msg_count} 則訊息")
    
    finally:
        # 關閉資料庫連線
        await db.close_db()


async def main():
    """主函式"""
    await check_line_data()


if __name__ == "__main__":
    asyncio.run(main())

