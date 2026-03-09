"""
提問管理服務
處理提問的 CRUD 操作、狀態管理、去識別化等
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from fastapi import BackgroundTasks
from ..database import db
from ..models.schemas import (
    Question, QuestionCreate, QuestionStatus,
    DifficultyLevel, AIAnalysisResult
)
from ..utils.security import generate_pseudonym
from .course_service import course_service
from .ai_service import ai_service


class QuestionService:
    """提問管理服務類別"""
    
    def __init__(self):
        self.collection_name = "questions"
    
    async def create_question(self, question_data: QuestionCreate, background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        建立新提問 (從 Line Bot 接收)
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
        
        # 去識別化處理
        pseudonym = generate_pseudonym(question_data.line_user_id)
        
        # 建立提問文件
        question_doc = {
            "course_id": question_data.course_id,
            "class_id": getattr(question_data, 'class_id', None), 
            "pseudonym": pseudonym,  
            "question_text": question_data.question_text,
            "status": QuestionStatus.PENDING,
            "cluster_id": None,
            "difficulty_score": None,
            "difficulty_level": None,
            "keywords": [],
            "merged_to_qa_id": None,
            "is_merged": False,
            "source": "LINE",  
            "original_message_id": getattr(question_data, 'original_message_id', None),
            "reply_to_qa_id": getattr(question_data, 'reply_to_qa_id', None),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.insert_one(question_doc)
        new_question_id = str(result.inserted_id)
        question_doc["_id"] = new_question_id

        # 啟動背景任務進行 AI 分析 (如果這是一般提問才分析)
        if background_tasks and not question_doc.get("reply_to_qa_id"):
            background_tasks.add_task(self.process_new_question_ai, new_question_id, question_data.question_text)

        return question_doc
    
    async def process_new_question_ai(self, question_id: str, question_text: str):
        """
        [背景任務] 執行 AI 分析並更新資料庫
        """
        try:
            print(f"🤖 開始 AI 分析提問: {question_id}")
            
            # 1. 執行深度分析 (關鍵字、難度、摘要)
            analysis_data = ai_service.analyze_question(question_text)
            
            # 2. 生成回答草稿
            draft = ai_service.generate_response_draft(question_text)
            
            # 3. 組合結果
            analysis_result = AIAnalysisResult(
                question_id=question_id,
                difficulty_score=analysis_data.get("difficulty_score", 0.5),
                keywords=analysis_data.get("keywords", []),
                cluster_id=None, # 暫時不分群
                response_draft=draft,
                summary=analysis_data.get("summary", ""),
                sentiment_score=0.0 # 暫時預設
            )
            
            await self.update_ai_analysis(question_id, analysis_result)
            print(f"✅ AI 分析完成: {question_id}")
            
        except Exception as e:
            print(f"❌ AI 背景任務失敗: {str(e)}")
            import traceback
            traceback.print_exc()

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
        """取得課程的提問列表"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {
            "reply_to_qa_id": None 
        }
        
        if course_id:
            query["course_id"] = course_id
        if class_id:
            query["class_id"] = class_id
        if status:
            query["status"] = status
        else:
            query["status"] = {"$ne": QuestionStatus.DELETED}
        
        cursor = collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        questions = await cursor.to_list(length=limit)
        
        for q in questions:
            q["_id"] = str(q["_id"])
        
        return questions
    
    async def update_question_status(
        self,
        question_id: str,
        new_status: QuestionStatus,
        rejection_reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新提問狀態"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        question = await self.get_question(question_id)
        if not question:
            return None
        
        current_status = question["status"]
        
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
        
        if new_status == QuestionStatus.DELETED:
            pass  
        elif current_status not in allowed_transitions:
            raise ValueError(f"狀態 {current_status} 無法變更")
        elif new_status not in allowed_transitions[current_status]:
            raise ValueError(f"無法從 {current_status} 轉換至 {new_status}")
        
        update_data = {
            "status": new_status,
            "updated_at": datetime.utcnow()
        }
        
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
        """更新 AI 分析結果"""
        database = db.get_db()
        collection = database[self.collection_name]
        
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
            "ai_response_draft": getattr(analysis_result, "response_draft", None),
            "ai_summary": getattr(analysis_result, "summary", None),
            "sentiment_score": getattr(analysis_result, "sentiment_score", None),
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
        """將多個提問合併至 Q&A"""
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
        """取得待 AI 分析的提問"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        cursor = collection.find({
            "course_id": course_id,
            "status": QuestionStatus.PENDING,
            "cluster_id": None,
            "reply_to_qa_id": None
        }).limit(limit)
        
        questions = await cursor.to_list(length=limit)
        
        ai_questions = []
        for q in questions:
            ai_questions.append({
                "_id": str(q["_id"]),
                "pseudonym": q["pseudonym"],  
                "question_text": q["question_text"],
                "created_at": q["created_at"]
            })
        
        return ai_questions

    # =========== 🔥 核心升級：專門撈取 Q&A 回答給 AI 批閱聚類的函式 ===========
    async def get_replies_for_clustering(
        self,
        qa_id: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """取得特定 Q&A 且尚未被聚類的學生回答"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 條件：是對此題目的回覆，且還沒被分派到任何聚類群組
        cursor = collection.find({
            "reply_to_qa_id": qa_id,
            "cluster_id": None
        }).limit(limit)
        
        replies = await cursor.to_list(length=limit)
        
        ai_replies = []
        for r in replies:
            ai_replies.append({
                "_id": str(r["_id"]),
                "pseudonym": r.get("pseudonym", "匿名"),  
                "answer_text": r["question_text"], # 雖然原本設計叫 question_text，但對於 Q&A 來說這是學生的「作答內容」
                "created_at": r["created_at"]
            })
        
        return ai_replies
    # ====================================================================
    
    async def delete_question(self, question_id: str) -> bool:
        """刪除提問"""
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
        
        query: Dict[str, Any] = {
            "course_id": course_id,
            "reply_to_qa_id": None
        }
        
        if class_id:
            query["class_id"] = class_id
        
        query["status"] = {"$ne": QuestionStatus.DELETED}
        
        cursor = collection.find(query)
        questions = await cursor.to_list(length=None)
        
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
        
        for q in questions:
            status = q.get("status", "")
            if status:
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
            
            difficulty_level = q.get("difficulty_level")
            if difficulty_level:
                if difficulty_level == DifficultyLevel.EASY or difficulty_level == "easy":
                    difficulty_distribution["easy"] += 1
                elif difficulty_level == DifficultyLevel.MEDIUM or difficulty_level == "medium":
                    difficulty_distribution["medium"] += 1
                elif difficulty_level == DifficultyLevel.HARD or difficulty_level == "hard":
                    difficulty_distribution["hard"] += 1
            
            difficulty_score = q.get("difficulty_score")
            if difficulty_score is not None:
                difficulty_scores.append(difficulty_score)
            
            cluster_id = q.get("cluster_id")
            if cluster_id:
                cluster_ids.add(cluster_id)
        
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