"""
建立測試 LINE 訊息資料
用於測試 LINE 整合功能
"""
import asyncio
from datetime import datetime, timedelta
import random
from app.database import db
from app.utils.security import generate_pseudonym

# 模擬的學生問題
SAMPLE_QUESTIONS = [
    "Python 的迴圈怎麼寫？",
    "期中考的範圍是什麼？",
    "作業繳交期限是什麼時候？",
    "如何安裝 numpy？",
    "物件導向程式設計是什麼？",
    "演算法複雜度如何計算？",
    "資料結構有哪些種類？",
    "什麼是遞迴？",
    "如何除錯程式？",
    "期末專題題目有哪些？"
]

# 模擬的系統回覆
SAMPLE_REPLIES = [
    "您可以參考課程第 3 章的內容...",
    "期中考範圍是第 1-5 章，詳細資訊請查看公告",
    "作業繳交期限是本週五晚上 11:59",
    "可以使用 pip install numpy 來安裝",
    "物件導向是一種程式設計典範，詳細說明請參考教材",
    "時間複雜度通常用 Big O 表示法來表示",
    "常見的資料結構包括陣列、鏈結串列、堆疊、佇列等",
    "遞迴是函式呼叫自己的程式設計技巧",
    "可以使用 print() 或除錯工具來追蹤程式執行",
    "期末專題題目會在下週公告"
]

async def create_test_messages():
    """建立測試訊息"""
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    # 清除現有的測試資料（可選）
    print("清除現有的測試資料...")
    await messages_collection.delete_many({})
    
    # 產生過去 7 天的測試資料
    print("開始產生測試資料...")
    now = datetime.utcnow()
    
    # 模擬 5 個不同的學生
    test_users = [
        f"U{str(i).zfill(32)}" for i in range(1, 6)
    ]
    
    messages_to_insert = []
    
    for day_offset in range(7):
        date = now - timedelta(days=6-day_offset)
        # 每天隨機產生 10-20 組對話
        num_conversations = random.randint(10, 20)
        
        for conv in range(num_conversations):
            # 隨機選擇一個學生
            user_id = random.choice(test_users)
            pseudonym = generate_pseudonym(user_id)
            
            # 隨機時間
            hour = random.randint(8, 22)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            
            timestamp = date.replace(
                hour=hour,
                minute=minute,
                second=second
            )
            
            # 學生問題
            question = random.choice(SAMPLE_QUESTIONS)
            received_msg = {
                "user_id": user_id,
                "pseudonym": pseudonym,
                "message_type": "text",
                "direction": "received",
                "content": question,
                "line_message_id": f"msg_{timestamp.timestamp()}_{random.randint(1000, 9999)}",
                "created_at": timestamp
            }
            messages_to_insert.append(received_msg)
            
            # 系統回覆（幾秒後）
            reply_timestamp = timestamp + timedelta(seconds=random.randint(5, 30))
            reply = random.choice(SAMPLE_REPLIES)
            
            # 90% 的機率成功發送
            if random.random() < 0.9:
                sent_msg = {
                    "user_id": user_id,
                    "pseudonym": pseudonym,
                    "message_type": "text",
                    "direction": "sent",
                    "content": reply,
                    "created_at": reply_timestamp
                }
            else:
                # 10% 的機率發送失敗
                sent_msg = {
                    "user_id": user_id,
                    "pseudonym": pseudonym,
                    "message_type": "text",
                    "direction": "failed",
                    "content": reply,
                    "error_message": "發送失敗：網路連線逾時",
                    "created_at": reply_timestamp
                }
            messages_to_insert.append(sent_msg)
    
    # 批次插入
    if messages_to_insert:
        result = await messages_collection.insert_many(messages_to_insert)
        print(f"成功建立 {len(result.inserted_ids)} 筆測試訊息資料")
        
        # 統計資訊
        received_count = sum(1 for msg in messages_to_insert if msg["direction"] == "received")
        sent_count = sum(1 for msg in messages_to_insert if msg["direction"] == "sent")
        failed_count = sum(1 for msg in messages_to_insert if msg["direction"] == "failed")
        
        print(f"\n統計資訊：")
        print(f"  收到的訊息：{received_count}")
        print(f"  發送的訊息：{sent_count}")
        print(f"  失敗的訊息：{failed_count}")
        print(f"  唯一用戶數：{len(test_users)}")
    else:
        print("沒有資料需要插入")

async def main():
    """主函式"""
    print("=" * 50)
    print("建立測試 LINE 訊息資料")
    print("=" * 50)
    
    # 連接資料庫
    print("連接資料庫...")
    await db.connect_db()
    
    try:
        await create_test_messages()
        print("\n✅ 測試資料建立完成！")
        print("您現在可以在前端 LINE 整合頁面看到這些測試資料了。")
    finally:
        # 關閉資料庫連線
        await db.close_db()

if __name__ == "__main__":
    asyncio.run(main())

