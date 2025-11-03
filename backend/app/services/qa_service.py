"""
Q&A 與公告管理服務
處理 Q&A 內容的建立、編輯、發布等功能
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from ..database import db
from ..models.schemas import QACreate, AnnouncementCreate


class QAService:
    """Q&A 管理服務類別"""
    
    def __init__(self):
        self.collection_name = "qas"
    
    async def create_qa(
        self,
        qa_data: QACreate,
        created_by: str
    ) -> Dict[str, Any]:
        """建立新 Q&A"""
        database = db.get_db()
        
        # 驗證課程是否存在
        courses_collection = database["courses"]
        course = await courses_collection.find_one({"_id": ObjectId(qa_data.course_id)})
        if not course:
            raise ValueError(f"課程不存在: {qa_data.course_id}")
        
        collection = database[self.collection_name]
        
        qa_doc = {
            **qa_data.model_dump(),
            "created_by": created_by,
            "related_question_ids": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # 如果立即發布，設定發布時間
        if qa_data.is_published:
            qa_doc["publish_date"] = datetime.utcnow()
        
        result = await collection.insert_one(qa_doc)
        qa_doc["_id"] = str(result.inserted_id)
        
        return qa_doc
    
    async def get_qa(self, qa_id: str) -> Optional[Dict[str, Any]]:
        """取得單一 Q&A"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        qa = await collection.find_one({"_id": ObjectId(qa_id)})
        if qa:
            qa["_id"] = str(qa["_id"])
        return qa
    
    async def get_qas_by_course(
        self,
        course_id: Optional[str] = None,
        class_id: Optional[str] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """取得課程的 Q&A 列表"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {}
        
        if course_id:
            query["course_id"] = course_id
        
        if class_id:
            query["$or"] = [
                {"class_id": class_id},
                {"class_id": None}  # 全課程 Q&A
            ]
        
        if is_published is not None:
            query["is_published"] = is_published
        
        cursor = collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        qas = await cursor.to_list(length=limit)
        
        for q in qas:
            q["_id"] = str(q["_id"])
        
        return qas
    
    async def update_qa(
        self,
        qa_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新 Q&A"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # 如果變更為發布狀態，設定發布時間
        if update_data.get("is_published") and not update_data.get("publish_date"):
            update_data["publish_date"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(qa_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_qa(qa_id)
        return None
    
    async def link_questions_to_qa(
        self,
        qa_id: str,
        question_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        將提問連結至 Q&A
        
        同時更新 Q&A 的 related_question_ids 和提問的 merged_to_qa_id
        """
        database = db.get_db()
        
        # 更新 Q&A
        qa_collection = database[self.collection_name]
        await qa_collection.update_one(
            {"_id": ObjectId(qa_id)},
            {
                "$addToSet": {
                    "related_question_ids": {"$each": question_ids}
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # 更新提問
        question_collection = database["questions"]
        question_object_ids = [ObjectId(qid) for qid in question_ids]
        await question_collection.update_many(
            {"_id": {"$in": question_object_ids}},
            {
                "$set": {
                    "merged_to_qa_id": qa_id,
                    "is_merged": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return await self.get_qa(qa_id)
    
    async def delete_qa(self, qa_id: str) -> bool:
        """刪除 Q&A (硬刪除)"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        result = await collection.delete_one({"_id": ObjectId(qa_id)})
        return result.deleted_count > 0
    
    async def search_qas(
        self,
        course_id: str,
        keyword: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """搜尋 Q&A"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 使用正則表達式搜尋問題或答案
        query = {
            "course_id": course_id,
            "$or": [
                {"question": {"$regex": keyword, "$options": "i"}},
                {"answer": {"$regex": keyword, "$options": "i"}},
                {"tags": {"$in": [keyword]}}
            ]
        }
        
        cursor = collection.find(query).skip(skip).limit(limit)
        qas = await cursor.to_list(length=limit)
        
        for q in qas:
            q["_id"] = str(q["_id"])
        
        return qas


class AnnouncementService:
    """公告管理服務類別"""
    
    def __init__(self):
        self.collection_name = "announcements"
    
    async def create_announcement(
        self,
        announcement_data: AnnouncementCreate,
        created_by: str
    ) -> Dict[str, Any]:
        """建立新公告"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        announcement_doc = {
            **announcement_data.model_dump(),
            "created_by": created_by,
            "sent_to_line": False,
            "line_message_id": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # 如果立即發布，設定發布時間
        if announcement_data.is_published:
            announcement_doc["publish_date"] = datetime.utcnow()
        
        result = await collection.insert_one(announcement_doc)
        announcement_doc["_id"] = str(result.inserted_id)
        
        return announcement_doc
    
    async def get_announcement(self, announcement_id: str) -> Optional[Dict[str, Any]]:
        """取得單一公告"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        announcement = await collection.find_one({"_id": ObjectId(announcement_id)})
        if announcement:
            announcement["_id"] = str(announcement["_id"])
        return announcement
    
    async def get_announcements_by_course(
        self,
        course_id: Optional[str] = None,
        class_id: Optional[str] = None,
        is_published: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """取得課程的公告列表"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {}
        
        if course_id:
            query["course_id"] = course_id
        
        if class_id:
            query["$or"] = [
                {"class_id": class_id},
                {"class_id": None}  # 全課程公告
            ]
        
        if is_published is not None:
            query["is_published"] = is_published
        
        cursor = collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        announcements = await cursor.to_list(length=limit)
        
        for a in announcements:
            a["_id"] = str(a["_id"])
        
        return announcements
    
    async def update_announcement(
        self,
        announcement_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新公告"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # 如果變更為發布狀態，設定發布時間
        if update_data.get("is_published") and not update_data.get("publish_date"):
            update_data["publish_date"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_announcement(announcement_id)
        return None
    
    async def mark_sent_to_line(
        self,
        announcement_id: str,
        line_message_id: str
    ) -> Optional[Dict[str, Any]]:
        """標記公告已發送至 Line"""
        return await self.update_announcement(
            announcement_id,
            {
                "sent_to_line": True,
                "line_message_id": line_message_id
            }
        )
    
    async def delete_announcement(self, announcement_id: str) -> bool:
        """刪除公告 (硬刪除)"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        result = await collection.delete_one({"_id": ObjectId(announcement_id)})
        return result.deleted_count > 0


# 全域服務實例
qa_service = QAService()
announcement_service = AnnouncementService()

