"""
提問管理服務
處理提問的 CRUD 操作、狀態管理、去識別化等
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from ..database import db
from ..models.schemas import (
    Question, QuestionCreate, QuestionStatus,
    DifficultyLevel, AIAnalysisResult
)
from ..utils.security import generate_pseudonym
from .course_service import course_service


class QuestionService:
    """提問管理服務類別"""
    
    def __init__(self):
        self.collection_name = "questions"
    
    async def create_question(self, question_data: QuestionCreate) -> Dict[str, Any]:
        """
        建立新提問 (從 Line Bot 接收)
        
        重要：此方法會自動進行去識別化處理
        
        Args:
            question_data: 提問資料 (包含 line_user_id)
        
        Returns:
            建立的提問文件
        
        Raises:
            ValueError: 當課程不存在時
        """
        # 驗證課程是否存在
        course = await course_service.get_course(question_data.course_id)
        if not course:
            raise ValueError(f"課程不存在: {question_data.course_id}")
        
        # 驗證課程是否為啟用狀態
        if not course.get("is_active", False):
            raise ValueError(f"課程已停用: {question_data.course_id}")
        
        database = db.get_db()
        collection = database[self.collection_name]
        
        # ⚠️ 關鍵步驟：去識別化處理
        pseudonym = generate_pseudonym(question_data.line_user_id)
        
        # 建立提問文件 (不包含原始 line_user_id)
        question_doc = {
            "course_id": question_data.course_id,
            "class_id": question_data.class_id,
            "pseudonym": pseudonym,  # 使用去識別化代號
            "question_text": question_data.question_text,
            "status": QuestionStatus.PENDING,
            "cluster_id": None,
            "difficulty_score": None,
            "difficulty_level": None,
            "keywords": [],
            "merged_to_qa_id": None,
            "is_merged": False,
            "original_message_id": question_data.original_message_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.insert_one(question_doc)
        question_doc["_id"] = str(result.inserted_id)
        
        return question_doc
    
    async def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """取得單一提問"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        question = await collection.find_one({"_id": ObjectId(question_id)})
        if question:
            question["_id"] = str(question["_id"])
        return question
    
    async def get_questions_by_course(
        self,
        course_id: Optional[str] = None,
        class_id: Optional[str] = None,
        status: Optional[QuestionStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        取得課程的提問列表
        
        Args:
            course_id: 課程ID (可選，不傳則查詢所有課程)
            class_id: 班級ID (可選)
            status: 提問狀態 (可選)
            skip: 跳過筆數
            limit: 限制筆數
        
        Note:
            默認會排除 DELETED 狀態的提問，除非明確指定 status 為 DELETED
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 建立查詢條件
        query: Dict[str, Any] = {}
        if course_id:
            query["course_id"] = course_id
        if class_id:
            query["class_id"] = class_id
        if status:
            query["status"] = status
        else:
            # 如果沒有指定狀態，默認排除已刪除的提問
            query["status"] = {"$ne": QuestionStatus.DELETED}
        
        cursor = collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        questions = await cursor.to_list(length=limit)
        
        # 轉換 ObjectId
        for q in questions:
            q["_id"] = str(q["_id"])
        
        return questions
    
    async def update_question_status(
        self,
        question_id: str,
        new_status: QuestionStatus,
        rejection_reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新提問狀態
        
        實作狀態機邏輯：
        - PENDING -> APPROVED, REJECTED, DELETED
        - APPROVED -> DELETED
        - 其他狀態不可變更
        
        Args:
            question_id: 提問ID
            new_status: 新狀態
            rejection_reason: 拒絕原因（當狀態為 REJECTED 時使用）
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 取得當前提問
        question = await self.get_question(question_id)
        if not question:
            return None
        
        current_status = question["status"]
        
        # 驗證狀態轉換是否合法
        allowed_transitions = {
            QuestionStatus.PENDING: [
                QuestionStatus.APPROVED,
                QuestionStatus.REJECTED,
                QuestionStatus.DELETED,
                QuestionStatus.WITHDRAWN
            ],
            QuestionStatus.APPROVED: [QuestionStatus.DELETED],
            QuestionStatus.REJECTED: [QuestionStatus.DELETED],
            QuestionStatus.WITHDRAWN: [QuestionStatus.DELETED],
        }
        
        # 如果目標狀態是 DELETED，允許從任何狀態轉換
        if new_status == QuestionStatus.DELETED:
            pass  # 允許刪除
        elif current_status not in allowed_transitions:
            raise ValueError(f"狀態 {current_status} 無法變更")
        elif new_status not in allowed_transitions[current_status]:
            raise ValueError(f"無法從 {current_status} 轉換至 {new_status}")
        
        # 更新狀態
        update_data = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
        # 如果是拒絕狀態且有提供原因，記錄拒絕原因
        if new_status == QuestionStatus.REJECTED and rejection_reason:
            update_data["rejection_reason"] = rejection_reason
        
        result = await collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_question(question_id)
        return None
    
    async def update_ai_analysis(
        self,
        question_id: str,
        analysis_result: AIAnalysisResult
    ) -> Optional[Dict[str, Any]]:
        """
        更新 AI 分析結果
        
        Args:
            question_id: 提問ID
            analysis_result: AI 分析結果
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 根據 difficulty_score 計算 difficulty_level
        difficulty_level = None
        if analysis_result.difficulty_score is not None:
            if analysis_result.difficulty_score < 0.3:
                difficulty_level = DifficultyLevel.EASY
            elif analysis_result.difficulty_score < 0.7:
                difficulty_level = DifficultyLevel.MEDIUM
            else:
                difficulty_level = DifficultyLevel.HARD
        
        update_data = {
            "cluster_id": analysis_result.cluster_id,
            "difficulty_score": analysis_result.difficulty_score,
            "difficulty_level": difficulty_level,
            "keywords": analysis_result.keywords,
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_question(question_id)
        return None
    
    async def merge_questions_to_qa(
        self,
        question_ids: List[str],
        qa_id: str
    ) -> int:
        """
        將多個提問合併至 Q&A
        
        Args:
            question_ids: 提問ID列表
            qa_id: Q&A ID
        
        Returns:
            更新的提問數量
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        object_ids = [ObjectId(qid) for qid in question_ids]
        
        result = await collection.update_many(
            {"_id": {"$in": object_ids}},
            {
                "$set": {
                    "merged_to_qa_id": qa_id,
                    "is_merged": True,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count
    
    async def get_questions_by_cluster(
        self,
        course_id: str,
        cluster_id: str
    ) -> List[Dict[str, Any]]:
        """取得同一聚類的提問"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        cursor = collection.find({
            "course_id": course_id,
            "cluster_id": cluster_id,
            "is_merged": False
        })
        questions = await cursor.to_list(length=None)
        
        for q in questions:
            q["_id"] = str(q["_id"])
        
        return questions
    
    async def get_pending_questions_for_ai(
        self,
        course_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        取得待 AI 分析的提問
        
        返回尚未進行 AI 分析的提問 (cluster_id 為 None)
        僅包含去識別化後的資料
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        cursor = collection.find({
            "course_id": course_id,
            "status": QuestionStatus.PENDING,
            "cluster_id": None
        }).limit(limit)
        
        questions = await cursor.to_list(length=limit)
        
        # 僅返回 AI 需要的欄位 (確保不洩漏隱私)
        ai_questions = []
        for q in questions:
            ai_questions.append({
                "_id": str(q["_id"]),
                "pseudonym": q["pseudonym"],  # 去識別化代號
                "question_text": q["question_text"],
                "created_at": q["created_at"]
            })
        
        return ai_questions
    
    async def delete_question(self, question_id: str) -> bool:
        """刪除提問 (軟刪除：變更狀態為 DELETED)"""
        result = await self.update_question_status(
            question_id,
            QuestionStatus.DELETED
        )
        return result is not None
    
    async def get_statistics(
        self,
        course_id: str,
        class_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """取得提問統計資料"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {"course_id": course_id}
        if class_id:
            query["class_id"] = class_id
        
        # 排除已刪除的提問，保持與提問列表頁面一致
        query["status"] = {"$ne": QuestionStatus.DELETED}
        
        # 取得所有符合條件的提問
        cursor = collection.find(query)
        questions = await cursor.to_list(length=None)
        
        # 初始化統計
        total_questions = len(questions)
        pending_count = 0
        approved_count = 0
        rejected_count = 0
        deleted_count = 0
        withdrawn_count = 0
        
        status_distribution: Dict[str, int] = {}
        difficulty_distribution: Dict[str, int] = {
            "easy": 0,
            "medium": 0,
            "hard": 0
        }
        
        difficulty_scores = []
        cluster_count = 0
        cluster_ids = set()
        
        # 統計各種指標
        for q in questions:
            # 狀態統計
            status = q.get("status", "")
            if status:
                # 統一轉換為大寫進行比較
                status_upper = status.upper() if isinstance(status, str) else status
                
                if status_upper == QuestionStatus.PENDING or status_upper == "PENDING":
                    pending_count += 1
                    status_distribution["PENDING"] = status_distribution.get("PENDING", 0) + 1
                elif status_upper == QuestionStatus.APPROVED or status_upper == "APPROVED":
                    approved_count += 1
                    status_distribution["APPROVED"] = status_distribution.get("APPROVED", 0) + 1
                elif status_upper == QuestionStatus.REJECTED or status_upper == "REJECTED":
                    rejected_count += 1
                    status_distribution["REJECTED"] = status_distribution.get("REJECTED", 0) + 1
                elif status_upper == QuestionStatus.DELETED or status_upper == "DELETED":
                    deleted_count += 1
                    status_distribution["DELETED"] = status_distribution.get("DELETED", 0) + 1
                elif status_upper == QuestionStatus.WITHDRAWN or status_upper == "WITHDRAWN":
                    withdrawn_count += 1
                    status_distribution["WITHDRAWN"] = status_distribution.get("WITHDRAWN", 0) + 1
            
            # 難度分布統計
            difficulty_level = q.get("difficulty_level")
            if difficulty_level:
                if difficulty_level == DifficultyLevel.EASY or difficulty_level == "easy":
                    difficulty_distribution["easy"] += 1
                elif difficulty_level == DifficultyLevel.MEDIUM or difficulty_level == "medium":
                    difficulty_distribution["medium"] += 1
                elif difficulty_level == DifficultyLevel.HARD or difficulty_level == "hard":
                    difficulty_distribution["hard"] += 1
            
            # 難度分數統計
            difficulty_score = q.get("difficulty_score")
            if difficulty_score is not None:
                difficulty_scores.append(difficulty_score)
            
            # 聚類統計
            cluster_id = q.get("cluster_id")
            if cluster_id:
                cluster_ids.add(cluster_id)
        
        # 計算平均難度
        avg_difficulty_score = sum(difficulty_scores) / len(difficulty_scores) if difficulty_scores else 0.0
        cluster_count = len(cluster_ids)
        
        return {
            "total_questions": total_questions,
            "pending_questions": pending_count,
            "approved_questions": approved_count,
            "rejected_questions": rejected_count,
            "deleted_questions": deleted_count,
            "withdrawn_questions": withdrawn_count,
            "avg_difficulty_score": round(avg_difficulty_score, 2),
            "status_distribution": status_distribution,
            "difficulty_distribution": difficulty_distribution,
            "cluster_count": cluster_count
        }


# 全域服務實例
question_service = QuestionService()

