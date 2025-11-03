#!/usr/bin/env python3
"""
清除測試 LINE 訊息資料
僅保留真實的 LINE Bot 訊息
"""
import asyncio
from datetime import datetime
import sys
import os

# 添加 app 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import db


async def clear_test_data():
    """清除所有 LINE 訊息資料"""
    print("=" * 60)
    print("清除測試 LINE 訊息資料")
    print("=" * 60)
    
    # 連接資料庫
    print("\n連接資料庫...")
    await db.connect_db()
    
    try:
        database = db.get_db()
        messages_collection = database["line_messages"]
        
        # 顯示目前的資料統計
        total_count = await messages_collection.count_documents({})
        print(f"\n目前資料庫中有 {total_count} 筆 LINE 訊息")
        
        if total_count == 0:
            print("✅ 資料庫中沒有資料，無需清除")
            return
        
        # 詢問是否要清除
        print("\n⚠️  警告：這將會刪除所有 LINE 訊息資料（包括測試資料和真實資料）")
        print("如果您只想清除測試資料並保留真實訊息，請先確認。")
        print("\n選項：")
        print("  1. 清除所有資料")
        print("  2. 取消")
        
        choice = input("\n請選擇 (1/2): ").strip()
        
        if choice == "1":
            print("\n開始清除資料...")
            result = await messages_collection.delete_many({})
            print(f"✅ 成功刪除 {result.deleted_count} 筆資料")
            print("\n現在您可以接收真實的 LINE Bot 訊息了。")
            print("請確保：")
            print("  1. ngrok 正在運行")
            print("  2. LINE Webhook URL 已正確設定")
            print("  3. 透過 LINE 向您的 Bot 發送訊息測試")
        else:
            print("\n❌ 已取消清除操作")
    
    finally:
        # 關閉資料庫連線
        await db.close_db()


async def main():
    """主函式"""
    await clear_test_data()


if __name__ == "__main__":
    asyncio.run(main())

