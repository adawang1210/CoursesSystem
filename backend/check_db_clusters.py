import asyncio
import sys
import os

# 確保 Python 能找到 app 模組 (如果直接在 backend 資料夾執行)
sys.path.append(os.getcwd())

from app.database import db
from bson import ObjectId

async def check():
    print("正在嘗試連線至資料庫...")
    
    # ✅ 修正 1: 使用正確的連線方法名稱
    await db.connect_db()
    
    try:
        database = db.get_db()
        
        # 請確保這裡是用您截圖中那個顯示 "已聚類" 的課程 ID
        COURSE_ID = "69575f0aeed290fb8c7aa01a" 
        
        print(f"🔍 檢查課程 ID: {COURSE_ID}")

        # 1. 檢查 Questions (提問)
        # 注意：這邊我們同時檢查 String 格式和 ObjectId 格式的 course_id，以防萬一
        questions = await database["questions"].find({
            "$or": [
                {"course_id": COURSE_ID},
                {"course_id": ObjectId(COURSE_ID)}
            ]
        }).to_list(None)
        
        print(f"👉 找到 {len(questions)} 個問題")
        
        clustered_count = 0
        for q in questions:
            cid = q.get("cluster_id")
            print(f"   - 提問: {q.get('question_text')[:10]}...")
            print(f"     Status: {q.get('status')}, Cluster ID: {cid} (類型: {type(cid)})")
            if cid:
                clustered_count += 1
                
        print(f"📊 統計: 共 {clustered_count} 個問題有 cluster_id")

        # 2. 檢查 Clusters (聚類主題)
        clusters = await database["clusters"].find({
            "$or": [
                {"course_id": COURSE_ID},
                {"course_id": ObjectId(COURSE_ID)}
            ]
        }).to_list(None)
        
        print(f"👉 找到 {len(clusters)} 個主題 (Clusters)")
        for c in clusters:
            print(f"   - 主題名稱: {c.get('topic_label')}")
            print(f"     ID: {c['_id']} (類型: {type(c['_id'])})")
            print(f"     原始資料: {c}")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
    finally:
        # ✅ 修正 2: 使用正確的關閉方法名稱
        await db.close_db()

if __name__ == "__main__":
    # Windows 系統有時需要設定 EventLoopPolicy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())