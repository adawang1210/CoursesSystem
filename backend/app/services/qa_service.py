"""
Q&A 與公告管理服務
處理 Q&A 內容的建立、編輯、發布等功能
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
from bson import ObjectId
from ..database import db
from ..models.schemas import QACreate, AnnouncementCreate
from .line_service import line_service  # 🔥 引入 line_service 準備做推播


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
        
        qa_dict = qa_data.model_dump()
        
        # =========== 🔥 處理限時互動時間計算 ===========
        expires_at = None
        if qa_dict.get("allow_replies") and qa_dict.get("duration_minutes"):
            expires_at = datetime.utcnow() + timedelta(minutes=qa_dict["duration_minutes"])
        # ==========================================
        
        qa_doc = {
            **qa_dict,
            "expires_at": expires_at,
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
        
        # =========== 🔥 觸發 LINE 推播廣播 ===========
        if qa_data.is_published:
            asyncio.create_task(
                line_service.broadcast_qa_to_course(qa_data.course_id, qa_doc)
            )
        # ==========================================
        
        return qa_doc
    
    async def get_qa(self, qa_id: str) -> Optional[Dict[str, Any]]:
        """取得單一 Q&A"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        qa = await collection.find_one({"_id": ObjectId(qa_id)})
        if qa:
            qa["_id"] = str(qa["_id"])
        return qa

    async def get_qa_replies(self, qa_id: str) -> List[Dict[str, Any]]:
        """取得特定 Q&A 的所有學生回覆"""
        database = db.get_db()
        collection = database["questions"]
        
        cursor = collection.find({"reply_to_qa_id": qa_id}).sort("created_at", 1)
        replies = await cursor.to_list(length=None)
        
        for r in replies:
            r["_id"] = str(r["_id"])
        
        return replies
    
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
                {"class_id": None}
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
        """將提問連結至 Q&A"""
        database = db.get_db()
        
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


# =========================================================================
# 🔥 以下為 AnnouncementService 修改重點區域
# =========================================================================
class AnnouncementService:
    """公告管理服務類別"""
    
    def __init__(self):
        self.collection_name = "announcements"
    
    async def create_announcement(
        self,
        announcement_data: AnnouncementCreate,
        created_by: str
    ) -> Dict[str, Any]:
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
        
        if announcement_data.is_published:
            announcement_doc["publish_date"] = datetime.utcnow()
            # 🔥 新增：標記將送出至 LINE
            announcement_doc["sent_to_line"] = True
        
        result = await collection.insert_one(announcement_doc)
        announcement_doc["_id"] = str(result.inserted_id)
        
        # =========== 🔥 新增：如果建立時就勾選發布，立刻推播！ ===========
        if announcement_data.is_published:
            asyncio.create_task(
                line_service.broadcast_announcement_to_course(announcement_data.course_id, announcement_doc)
            )
        # =============================================================
        
        return announcement_doc
    
    async def get_announcement(self, announcement_id: str) -> Optional[Dict[str, Any]]:
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
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {}
        
        if course_id:
            query["course_id"] = course_id
        
        if class_id:
            query["$or"] = [
                {"class_id": class_id},
                {"class_id": None}
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
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 先取得原本的狀態，用來比對是不是「剛剛才被改為發布」
        old_announcement = await self.get_announcement(announcement_id)
        if not old_announcement:
            return None

        update_data["updated_at"] = datetime.utcnow()
        
        # =========== 🔥 判斷是否為「草稿轉發布」 ===========
        is_newly_published = False
        if update_data.get("is_published") and not old_announcement.get("is_published"):
            update_data["publish_date"] = datetime.utcnow()
            update_data["sent_to_line"] = True
            is_newly_published = True
        # ===============================================
        
        result = await collection.update_one(
            {"_id": ObjectId(announcement_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            updated_doc = await self.get_announcement(announcement_id)
            
            # 🔥 如果是從草稿改為發布，觸發推播
            if is_newly_published and updated_doc:
                asyncio.create_task(
                    line_service.broadcast_announcement_to_course(updated_doc["course_id"], updated_doc)
                )
                
            return updated_doc
        return None
    
    async def mark_sent_to_line(
        self,
        announcement_id: str,
        line_message_id: str
    ) -> Optional[Dict[str, Any]]:
        return await self.update_announcement(
            announcement_id,
            {
                "sent_to_line": True,
                "line_message_id": line_message_id
            }
        )
    
    async def delete_announcement(self, announcement_id: str) -> bool:
        database = db.get_db()
        collection = database[self.collection_name]
        
        result = await collection.delete_one({"_id": ObjectId(announcement_id)})
        return result.deleted_count > 0


# 全域服務實例
qa_service = QAService()
announcement_service = AnnouncementService()