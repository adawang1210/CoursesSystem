#!/usr/bin/env python3
"""
MongoDB 數據庫查看工具
用於快速查看 courses_system 數據庫的內容
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import sys
import os

# 添加 app 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings


async def view_database():
    """查看數據庫內容"""
    print("=" * 60)
    print("MongoDB 數據庫內容查看工具")
    print("=" * 60)
    print(f"\n數據庫: {settings.MONGODB_DB_NAME}")
    print(f"連接: {settings.MONGODB_URI}\n")
    print("=" * 60)
    
    # 連接數據庫
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    
    # 獲取所有集合
    collections = await db.list_collection_names()
    
    print("\n所有集合 (Collections):")
    print("-" * 60)
    for collection_name in collections:
        count = await db[collection_name].count_documents({})
        print(f"  ✓ {collection_name} ({count} 筆資料)")
    
    print("\n" + "=" * 60)
    print("各集合詳細資料:")
    print("=" * 60)
    
    # 顯示課程資料
    print("\n課程 (courses):")
    print("-" * 60)
    async for course in db.courses.find().limit(5):
        print(f"\nID: {course.get('_id')}")
        print(f"課程代碼: {course.get('course_code')}")
        print(f"課程名稱: {course.get('course_name')}")
        print(f"教師姓名: {course.get('teacher_name')}")
        print(f"學期: {course.get('semester')}")
        print(f"建立時間: {course.get('created_at')}")
    
    # 顯示問題資料
    print("\n\n問題 (questions):")
    print("-" * 60)
    async for question in db.questions.find().limit(5):
        print(f"\nID: {question.get('_id')}")
        print(f"問題類型: {question.get('question_type')}")
        print(f"問題文本: {question.get('question_text')[:100]}...")
        print(f"課程ID: {question.get('course_id')}")
        print(f"建立時間: {question.get('created_at')}")
    
    # 顯示問答資料
    print("\n\n問答 (qas):")
    print("-" * 60)
    async for qa in db.qas.find().limit(5):
        print(f"\nID: {qa.get('_id')}")
        print(f"學生ID: {qa.get('student_id')}")
        print(f"問題: {qa.get('question')[:100]}...")
        if qa.get('answer'):
            print(f"回答: {qa.get('answer')[:100]}...")
        print(f"狀態: {qa.get('status')}")
        print(f"建立時間: {qa.get('created_at')}")
    
    # 顯示公告資料
    print("\n\n公告 (announcements):")
    print("-" * 60)
    async for announcement in db.announcements.find().limit(5):
        print(f"\nID: {announcement.get('_id')}")
        print(f"標題: {announcement.get('title')}")
        print(f"內容: {announcement.get('content')[:100]}...")
        print(f"課程ID: {announcement.get('course_id')}")
        print(f"建立時間: {announcement.get('created_at')}")
    
    print("\n" + "=" * 60)
    print("查詢完成！")
    print("\n提示：")
    print("  • 使用 MongoDB Compass 可獲得更好的視覺化體驗")
    print("  • 使用 mongosh 可進行互動式查詢")
    print("  • 每個集合只顯示前 5 筆資料")
    print("=" * 60)
    
    # 關閉連接
    client.close()


async def view_specific_collection(collection_name: str, limit: int = 10):
    """查看特定集合的內容"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]
    
    print(f"\n集合: {collection_name}")
    print("=" * 60)
    
    count = await db[collection_name].count_documents({})
    print(f"總筆數: {count}\n")
    
    async for doc in db[collection_name].find().limit(limit):
        print(doc)
        print("-" * 60)
    
    client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 查看特定集合
        collection = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        asyncio.run(view_specific_collection(collection, limit))
    else:
        # 查看所有集合概覽
        asyncio.run(view_database())

