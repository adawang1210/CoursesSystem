"""
建立測試資料腳本
用於測試統計功能
"""
import asyncio
from datetime import datetime, timedelta
import random
from app.database import db
from app.models.schemas import QuestionStatus, DifficultyLevel
from app.utils.security import generate_pseudonym

async def create_test_data():
    """建立測試資料"""
    
    # 連接資料庫
    await db.connect_db()
    database = db.get_db()
    
    # 清除現有測試資料（可選）
    print("清除現有測試資料...")
    # await database["courses"].delete_many({})
    # await database["questions"].delete_many({})
    # await database["qas"].delete_many({})
    
    # 建立測試課程
    print("建立測試課程...")
    course_data = {
        "course_code": "CS101",
        "course_name": "Python 基礎程式設計",
        "semester": "113-1",
        "description": "Python 程式設計入門課程",
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    result = await database["courses"].insert_one(course_data)
    course_id = str(result.inserted_id)
    print(f"課程建立成功，ID: {course_id}")
    
    # 建立測試提問
    print("建立測試提問...")
    questions_data = []
    
    # 提問範本
    question_templates = [
        "如何使用 Python 讀取檔案？",
        "什麼是變數？",
        "如何使用 for 迴圈？",
        "list 和 tuple 有什麼差別？",
        "如何處理例外？",
        "什麼是函數？",
        "如何使用字典？",
        "Python 的資料型態有哪些？",
        "如何安裝套件？",
        "什麼是物件導向程式設計？",
        "如何使用 class？",
        "import 是什麼意思？",
        "如何使用條件判斷？",
        "什麼是遞迴？",
        "如何除錯？",
    ]
    
    statuses = [
        QuestionStatus.PENDING,
        QuestionStatus.APPROVED,
        QuestionStatus.APPROVED,
        QuestionStatus.APPROVED,
        QuestionStatus.REJECTED,
        QuestionStatus.PENDING,
    ]
    
    difficulties = [
        (0.3, DifficultyLevel.EASY),
        (0.5, DifficultyLevel.MEDIUM),
        (0.8, DifficultyLevel.HARD),
    ]
    
    keywords_pool = [
        ["Python", "基礎", "語法"],
        ["資料結構", "list", "tuple"],
        ["迴圈", "for", "while"],
        ["函數", "定義", "呼叫"],
        ["物件導向", "class", "繼承"],
        ["檔案處理", "讀取", "寫入"],
        ["例外處理", "try", "except"],
        ["套件", "import", "安裝"],
    ]
    
    # 建立 50 個測試提問
    for i in range(50):
        question_text = random.choice(question_templates)
        status = random.choice(statuses)
        difficulty_score, difficulty_level = random.choice(difficulties)
        keywords = random.choice(keywords_pool)
        
        # 生成偽名
        pseudonym = generate_pseudonym(f"test_user_{i % 10}")
        
        # 隨機日期（過去 30 天內）
        days_ago = random.randint(0, 30)
        created_at = datetime.utcnow() - timedelta(days=days_ago)
        
        question = {
            "course_id": course_id,
            "class_id": None,
            "pseudonym": pseudonym,
            "question_text": f"{question_text} (測試問題 #{i+1})",
            "status": status.value,
            "cluster_id": f"cluster_{i % 5 + 1}",  # 5 個聚類
            "difficulty_score": difficulty_score,
            "difficulty_level": difficulty_level.value,
            "keywords": keywords,
            "is_merged": False,
            "merged_to_qa_id": None,
            "created_at": created_at,
            "updated_at": created_at
        }
        
        questions_data.append(question)
    
    if questions_data:
        await database["questions"].insert_many(questions_data)
        print(f"成功建立 {len(questions_data)} 個測試提問")
    
    # 建立測試 Q&A
    print("建立測試 Q&A...")
    qas_data = [
        {
            "course_id": course_id,
            "class_id": None,
            "question": "如何使用 Python 讀取檔案？",
            "answer": "使用 open() 函數搭配 with 語句來讀取檔案，例如：\n```python\nwith open('file.txt', 'r') as f:\n    content = f.read()\n```",
            "category": "檔案處理",
            "tags": ["Python", "檔案", "讀取"],
            "is_published": True,
            "publish_date": datetime.utcnow(),
            "related_question_ids": [],
            "created_by": "admin",
            "created_at": datetime.utcnow()
        },
        {
            "course_id": course_id,
            "class_id": None,
            "question": "list 和 tuple 有什麼差別？",
            "answer": "主要差別：\n1. list 是可變的（mutable），tuple 是不可變的（immutable）\n2. list 使用 []，tuple 使用 ()\n3. list 可以修改元素，tuple 不行",
            "category": "資料結構",
            "tags": ["Python", "list", "tuple", "資料結構"],
            "is_published": True,
            "publish_date": datetime.utcnow(),
            "related_question_ids": [],
            "created_by": "admin",
            "created_at": datetime.utcnow()
        },
        {
            "course_id": course_id,
            "class_id": None,
            "question": "什麼是物件導向程式設計？",
            "answer": "物件導向程式設計（OOP）是一種程式設計典範，將資料和操作資料的方法組織成「物件」。主要概念包括：\n- 封裝（Encapsulation）\n- 繼承（Inheritance）\n- 多型（Polymorphism）",
            "category": "物件導向",
            "tags": ["Python", "OOP", "物件導向", "class"],
            "is_published": True,
            "publish_date": datetime.utcnow(),
            "related_question_ids": [],
            "created_by": "admin",
            "created_at": datetime.utcnow()
        }
    ]
    
    if qas_data:
        await database["qas"].insert_many(qas_data)
        print(f"成功建立 {len(qas_data)} 個測試 Q&A")
    
    # 顯示統計
    print("\n=== 測試資料建立完成 ===")
    print(f"課程數量: 1")
    print(f"提問數量: {len(questions_data)}")
    print(f"Q&A 數量: {len(qas_data)}")
    print(f"\n課程 ID: {course_id}")
    print("\n請前往 http://localhost:3000/dashboard/statistics 查看統計資料")
    
    # 關閉資料庫連線
    await db.close_db()

if __name__ == "__main__":
    asyncio.run(create_test_data())

