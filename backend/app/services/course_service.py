"""
課程與班級管理服務
處理課程、班級的 CRUD 操作與同步
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from ..database import db
from ..models.schemas import CourseCreate, ClassCreate


class CourseService:
    """課程管理服務類別"""
    
    def __init__(self):
        self.collection_name = "courses"
    
    async def create_course(self, course_data: CourseCreate) -> Dict[str, Any]:
        """建立新課程"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        course_doc = {
            **course_data.model_dump(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.insert_one(course_doc)
        course_doc["_id"] = str(result.inserted_id)
        
        return course_doc
    
    async def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """取得單一課程"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        course = await collection.find_one({"_id": ObjectId(course_id)})
        if course:
            course["_id"] = str(course["_id"])
        return course
    
    async def get_courses(
        self,
        semester: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """取得課程列表"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {}
        if semester:
            query["semester"] = semester
        if is_active is not None:
            query["is_active"] = is_active
        
        cursor = collection.find(query).skip(skip).limit(limit)
        courses = await cursor.to_list(length=limit)
        
        # 獲取提問數統計
        questions_collection = database["questions"]
        
        for c in courses:
            course_id = str(c["_id"])
            c["_id"] = course_id
            
            # 計算此課程的提問總數（排除已刪除的提問）
            question_count = await questions_collection.count_documents({
                "course_id": course_id,
                "status": {"$ne": "DELETED"}
            })
            c["question_count"] = question_count
            
            # 計算此課程的學生數（去重的匿名ID，排除已刪除的提問）
            pipeline = [
                {"$match": {"course_id": course_id, "status": {"$ne": "DELETED"}}},
                {"$group": {"_id": "$anonymous_id"}},
                {"$count": "total"}
            ]
            student_stats = await questions_collection.aggregate(pipeline).to_list(length=1)
            c["student_count"] = student_stats[0]["total"] if student_stats else 0
        
        return courses
    
    async def update_course(
        self,
        course_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新課程"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(course_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_course(course_id)
        return None
    
    async def delete_course(self, course_id: str) -> bool:
        """
        刪除課程 (軟刪除)
        
        同時會級聯刪除相關資料：
        - 班級 (classes) - 軟刪除（設為 is_active: False）
        - 提問 (questions) - 軟刪除（設為 DELETED 狀態）
        - QA 對話 (qas) - 硬刪除
        - 公告 (announcements) - 硬刪除
        """
        database = db.get_db()
        
        # 1. 軟刪除課程本身
        result = await self.update_course(course_id, {"is_active": False})
        if result is None:
            return False
        
        # 2. 軟刪除相關的班級
        classes_collection = database["classes"]
        await classes_collection.update_many(
            {"course_id": course_id},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # 3. 軟刪除相關的提問（設為 DELETED 狀態）
        questions_collection = database["questions"]
        await questions_collection.update_many(
            {"course_id": course_id},
            {
                "$set": {
                    "status": "DELETED",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # 4. 硬刪除相關的 QA 對話
        qas_collection = database["qas"]
        await qas_collection.delete_many({"course_id": course_id})
        
        # 5. 硬刪除相關的公告
        announcements_collection = database["announcements"]
        await announcements_collection.delete_many({"course_id": course_id})
        
        return True
    
    async def sync_courses_from_external(
        self,
        courses_data: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        從外部系統同步課程資料
        
        Args:
            courses_data: 外部系統的課程資料列表
        
        Returns:
            同步結果統計 {"created": 數量, "updated": 數量}
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        created_count = 0
        updated_count = 0
        
        for course_data in courses_data:
            course_code = course_data.get("course_code")
            semester = course_data.get("semester")
            
            # 檢查課程是否已存在
            existing = await collection.find_one({
                "course_code": course_code,
                "semester": semester
            })
            
            if existing:
                # 更新現有課程
                await collection.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            **course_data,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                updated_count += 1
            else:
                # 建立新課程
                course_doc = {
                    **course_data,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                await collection.insert_one(course_doc)
                created_count += 1
        
        return {"created": created_count, "updated": updated_count}


class ClassService:
    """班級管理服務類別"""
    
    def __init__(self):
        self.collection_name = "classes"
    
    async def create_class(self, class_data: ClassCreate) -> Dict[str, Any]:
        """建立新班級"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        class_doc = {
            **class_data.model_dump(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.insert_one(class_doc)
        class_doc["_id"] = str(result.inserted_id)
        
        return class_doc
    
    async def get_class(self, class_id: str) -> Optional[Dict[str, Any]]:
        """取得單一班級"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        class_doc = await collection.find_one({"_id": ObjectId(class_id)})
        if class_doc:
            class_doc["_id"] = str(class_doc["_id"])
        return class_doc
    
    async def get_classes_by_course(
        self,
        course_id: str,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """取得課程的所有班級"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {"course_id": course_id}
        if is_active is not None:
            query["is_active"] = is_active
        
        cursor = collection.find(query)
        classes = await cursor.to_list(length=None)
        
        for c in classes:
            c["_id"] = str(c["_id"])
        
        return classes
    
    async def update_class(
        self,
        class_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新班級"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(class_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_class(class_id)
        return None
    
    async def delete_class(self, class_id: str) -> bool:
        """刪除班級 (軟刪除)"""
        result = await self.update_class(class_id, {"is_active": False})
        return result is not None


# 全域服務實例
course_service = CourseService()
class_service = ClassService()

