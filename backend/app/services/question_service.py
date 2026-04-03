"""
作答紀錄管理服務 (原提問管理)
處理學生對 Q&A 任務的作答、去識別化、批閱狀態與 AI 分析結果更新
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
from fastapi import BackgroundTasks
from ..database import db
from ..models.schemas import QuestionCreate, DifficultyLevel, AIAnalysisResult, ReviewStatus
from ..utils.security import generate_pseudonym
from .course_service import course_service


class QuestionService:
    """作答紀錄管理服務類別"""
    
    def __init__(self):
        # 為了相容舊資料與結構，資料表名稱維持 "questions"
        self.collection_name = "questions"
    
    async def create_question(self, question_data: QuestionCreate, background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        建立新提問/作答紀錄 (從 Line Bot 接收)
        """
        # 1. 驗證課程是否存在與啟用
        course = await course_service.get_course(question_data.course_id)
        if not course or not course.get("is_active", False):
            raise ValueError(f"課程不存在或已停用: {question_data.course_id}")
        
        database = db.get_db()
        collection = database[self.collection_name]
        
        # 2. 去識別化處理
        pseudonym = generate_pseudonym(question_data.line_user_id)
        
        # =========== 🔥 作答次數限制檢查 ===========
        qa_id = getattr(question_data, 'reply_to_qa_id', None)
        if qa_id:
            try:
                # 撈取這題 Q&A 的設定
                qa_doc = await database["qas"].find_one({"_id": ObjectId(qa_id)})
                if qa_doc:
                    max_attempts = qa_doc.get("max_attempts")
                    
                    # 如果老師有設定次數限制 (大於 0)
                    if max_attempts is not None and max_attempts > 0:
                        # 查詢該學生 (pseudonym) 在這題已作答的次數（不計退回的）
                        existing_count = await collection.count_documents({
                            "reply_to_qa_id": qa_id,
                            "pseudonym": pseudonym,
                            "review_status": {"$ne": "rejected"}
                        })
                        
                        if existing_count >= max_attempts:
                            raise ValueError(f"您已達到本題的最高作答次數上限 ({max_attempts} 次)！")
            except Exception as e:
                # 確保我們自定義的 ValueError 能順利往外拋
                if isinstance(e, ValueError):
                    raise e
                print(f"檢查作答次數時發生錯誤: {e}")
        # ===============================================

        # 3. 建立乾淨的作答紀錄文件
        question_doc = {
            "course_id": question_data.course_id,
            "class_id": getattr(question_data, 'class_id', None), 
            "pseudonym": pseudonym,  
            
            # =========== 🔥 新增：將學號存入作答紀錄 ===========
            "student_id": getattr(question_data, 'student_id', None),
            # ===============================================
            
            "question_text": question_data.question_text,
            
            "review_status": ReviewStatus.PENDING,
            "feedback": None,
            
            "cluster_id": None,
            "difficulty_score": None,
            "difficulty_level": None,
            "keywords": [],
            "source": "LINE",  
            "original_message_id": getattr(question_data, 'original_message_id', None),
            "reply_to_qa_id": getattr(question_data, 'reply_to_qa_id', None),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await collection.insert_one(question_doc)
        question_doc["_id"] = str(result.inserted_id)

        return question_doc

    async def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """取得單一作答紀錄"""
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
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """取得課程的作答紀錄列表"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        query: Dict[str, Any] = {}
        
        if course_id:
            query["course_id"] = course_id
        if class_id:
            query["class_id"] = class_id
        
        cursor = collection.find(query).skip(skip).limit(limit).sort("created_at", -1)
        questions = await cursor.to_list(length=limit)
        
        for q in questions:
            q["_id"] = str(q["_id"])
        
        return questions
    
    async def update_review_status(
        self,
        question_id: str,
        review_status: ReviewStatus,
        feedback: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """更新學生的作答批閱狀態與評語，退回時通知學生可重新作答"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        update_data = {
            "review_status": review_status,
            "updated_at": datetime.utcnow()
        }
        
        if feedback is not None:
            update_data["feedback"] = feedback
            
        result = await collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$set": update_data}
        )
        
        question = await self.get_question(question_id)

        # 退回時透過 LINE 通知學生可重新作答
        if question and review_status == ReviewStatus.REJECTED:
            await self._notify_rejection(question, feedback)

        return question

    async def _notify_rejection(self, question: Dict[str, Any], feedback: Optional[str] = None):
        """透過 LINE 推播通知學生作答被退回，可重新作答"""
        from ..config import settings
        if not settings.LINE_CHANNEL_ACCESS_TOKEN:
            return

        # 需要找到學生的 LINE user_id（從 pseudonym 反查 line_users）
        database = db.get_db()
        pseudonym = question.get("pseudonym")
        if not pseudonym:
            return

        # 從 line_messages 找到該 pseudonym 對應的 user_id
        msg_doc = await database["line_messages"].find_one({"pseudonym": pseudonym})
        if not msg_doc or not msg_doc.get("user_id"):
            return

        user_id = msg_doc["user_id"]

        feedback_text = f"\n\n💬 老師的評語：{feedback}" if feedback else ""
        text = (
            f"📋 您的作答已被老師退回，請重新作答。{feedback_text}\n\n"
            f"🔄 請直接在此重新輸入您的答案即可。"
        )

        try:
            from linebot.v3.messaging import (
                Configuration, AsyncApiClient, AsyncMessagingApi,
                PushMessageRequest, TextMessage,
            )
            configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
            async with AsyncApiClient(configuration) as api_client:
                line_bot_api = AsyncMessagingApi(api_client)
                await line_bot_api.push_message(
                    PushMessageRequest(to=user_id, messages=[TextMessage(text=text)])
                )
        except Exception as e:
            print(f"⚠️ 退回通知發送失敗: {e}")

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
    
    async def get_questions_by_cluster(
        self,
        course_id: str,
        cluster_id: str
    ) -> List[Dict[str, Any]]:
        """取得同一聚類的作答紀錄"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        cursor = collection.find({
            "course_id": course_id,
            "cluster_id": cluster_id
        })
        questions = await cursor.to_list(length=None)
        
        for q in questions:
            q["_id"] = str(q["_id"])
        
        return questions

    async def reset_clusters_for_qa(self, qa_id: str) -> int:
        """
        清除特定 Q&A 底下所有作答的 AI 聚類標記 (設回 None)
        這樣 AI 在重新聚類時，才會重新抓取到這些資料。
        """
        database = db.get_db()
        collection = database[self.collection_name]
        
        result = await collection.update_many(
            {"reply_to_qa_id": qa_id},
            {"$set": {
                "cluster_id": None,
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count

    async def get_replies_for_clustering(
        self,
        qa_id: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """取得特定 Q&A 且尚未被聚類的學生回答"""
        database = db.get_db()
        collection = database[self.collection_name]

        cursor = collection.find({
            "reply_to_qa_id": qa_id,
            "cluster_id": None,
            "review_status": ReviewStatus.APPROVED
        }).limit(limit)
        
        replies = await cursor.to_list(length=limit)
        
        ai_replies = []
        for r in replies:
            ai_replies.append({
                "_id": str(r["_id"]),
                "pseudonym": r.get("pseudonym", "匿名"),  
                "answer_text": r.get("question_text", ""), 
                "created_at": r.get("created_at")
            })
        
        return ai_replies
    
    async def delete_question(self, question_id: str) -> bool:
        """刪除作答紀錄 (直接實體刪除)"""
        database = db.get_db()
        collection = database[self.collection_name]
        
        result = await collection.delete_one({"_id": ObjectId(question_id)})
        return result.deleted_count > 0


# 全域服務實例
question_service = QuestionService()