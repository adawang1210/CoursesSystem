import asyncio
import sys
import os

# 設定路徑以匯入 app 模組
sys.path.append(os.getcwd())

from app.database import db
from bson import ObjectId

async def reset_course_data():
    print("🔄 正在連接資料庫...")
    await db.connect_db()
    
    try:
        database = db.get_db()
        
        # 🔥 請填入您的「研究方法」課程 ID
        COURSE_ID = "69575f0aeed290fb8c7aa01a" 
        
        print(f"🎯 目標課程 ID: {COURSE_ID}")

        # 1. 重置問題狀態 (把 cluster_id 變回 null)
        # 我們同時匹配 string 和 ObjectId 格式，確保萬無一失
        q_filter = {
            "$or": [
                {"course_id": COURSE_ID},
                {"course_id": ObjectId(COURSE_ID)}
            ]
        }
        
        update_result = await database["questions"].update_many(
            q_filter,
            {
                "$set": {
                    "cluster_id": None, # 清空分群
                    "status": "PENDING" # (選用) 如果您想讓狀態也變回待處理
                }
            }
        )
        print(f"✅ 已重置 {update_result.modified_count} 個問題的 cluster_id 為 None")

        # 2. 刪除舊的 Cluster 紀錄
        # 這樣前端才不會顯示舊的卡片
        c_filter = {
            "$or": [
                {"course_id": COURSE_ID},
                {"course_id": ObjectId(COURSE_ID)}
            ]
        }
        delete_result = await database["clusters"].delete_many(c_filter)
        print(f"🗑️ 已刪除 {delete_result.deleted_count} 個舊的 Cluster 主題")

        print("\n✨ 重置完成！現在您可以回到前端點擊「重新運行 AI 分析」了。")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        await db.close_db()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_course_data())