import asyncio
import sys
import os

# 設定路徑以匯入 app 模組
sys.path.append(os.getcwd())

from app.database import db
from bson import ObjectId

async def hard_delete_course_data():
    print("🔥 正在連接資料庫...")
    await db.connect_db()
    
    try:
        database = db.get_db()
        
        # ==========================================
        # 🎯 請確認您的課程 ID
        # ==========================================
        COURSE_ID = "69575f0aeed290fb8c7aa01a" 
        # ==========================================

        print(f"🎯 目標課程 ID: {COURSE_ID}")
        print("⚠️  警告：此操作將「永久刪除」該課程的所有資料，無法復原！")
        
        confirm = input("❓ 確定要執行刪除嗎？ (請輸入 'yes' 確認): ")
        if confirm.lower() != 'yes':
            print("❌ 操作已取消")
            return

        # 建立過濾條件 (同時支援 string 和 ObjectId 格式)
        filter_query = {
            "$or": [
                {"course_id": COURSE_ID},
                {"course_id": ObjectId(COURSE_ID)}
            ]
        }
        
        # 1. 刪除所有問題 (包含 PENDING, DELETED 等所有狀態)
        q_result = await database["questions"].delete_many(filter_query)
        print(f"🗑️  已永久刪除 {q_result.deleted_count} 筆問題 (Questions)")

        # 2. 刪除所有聚類結果
        c_result = await database["clusters"].delete_many(filter_query)
        print(f"🗑️  已永久刪除 {c_result.deleted_count} 筆聚類 (Clusters)")
        
        # 3. (選用) 刪除相關的 AI 分析紀錄 (若有獨立 Collection)
        # a_result = await database["ai_analysis_logs"].delete_many(filter_query)
        
        print("\n✨ 資料庫已清理乾淨！現在是一張白紙了。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        await db.close_db()

if __name__ == "__main__":
    # Windows 系統修正 asyncio loop 錯誤
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(hard_delete_course_data())