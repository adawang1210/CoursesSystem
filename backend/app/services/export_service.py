"""
資料匯出服務
提供 CSV 格式的統計資料匯出功能
"""
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..database import db
from ..models.schemas import QuestionStatus
from ..utils.datetime_helper import format_datetime


class ExportService:
    """資料匯出服務類別"""
    
    async def export_questions_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        匯出提問資料為 CSV 格式 (包含 AI 分析欄位)
        """
        database = db.get_db()
        collection = database["questions"]
        
        # 建立多維度查詢條件
        query: Dict[str, Any] = {"course_id": course_id, "status": {"$ne": "DELETED"}}
        
        if class_id:
            query["class_id"] = class_id

        if cluster_id:
            query["cluster_id"] = cluster_id
        
        # 時間區間過濾
        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date
        
        # 取得資料
        cursor = collection.find(query).sort("created_at", -1)
        questions = await cursor.to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題列
        writer.writerow([
            "提問ID", "去識別化代號", "提問內容", "狀態", "AI聚類ID",
            "難度分數", "難度等級", "關鍵字", "AI回答草稿", "AI摘要",
            "情緒分數", "是否已合併", "合併至Q&A ID", "建立時間", "更新時間"
        ])
        
        # 寫入資料列
        for q in questions:
            # 防呆：確保 keywords 不是 None，避免 join 報錯
            keywords = q.get("keywords") or []
            
            writer.writerow([
                str(q["_id"]),
                q.get("pseudonym", ""),
                q.get("question_text", ""),
                q.get("status", ""),
                q.get("cluster_id", ""),
                q.get("difficulty_score", ""),
                q.get("difficulty_level", ""),
                ", ".join(keywords),
                q.get("ai_response_draft", ""),
                q.get("ai_summary", ""),
                q.get("sentiment_score", ""),
                "是" if q.get("is_merged", False) else "否",
                q.get("merged_to_qa_id", ""),
                format_datetime(q.get("created_at")) if q.get("created_at") else "",
                format_datetime(q.get("updated_at")) if q.get("updated_at") else ""
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content


    async def export_clusters_to_csv(self, course_id: str) -> str:
        """
        匯出 AI 聚類主題分析報表
        """
        database = db.get_db()
        collection = database["clusters"]
        
        cursor = collection.find({"course_id": course_id}).sort("question_count", -1)
        clusters = await cursor.to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題
        writer.writerow([
            "聚類ID", "主題標籤 (Topic)", "綜合摘要 (Summary)", 
            "包含提問數", "平均難度", "關鍵字", "是否人工鎖定"
        ])
        
        # 處理資料
        for c in clusters:
            keywords = c.get("keywords") or []
            writer.writerow([
                str(c["_id"]),
                c.get("topic_label", ""),
                c.get("summary", ""),
                c.get("question_count", 0),
                f"{c.get('avg_difficulty', 0):.2f}",
                ", ".join(keywords),
                "是" if c.get("is_locked", False) else "否"
            ])
            
        csv_content = output.getvalue()
        output.close()
        
        return csv_content

    # =========== 🔥 核心升級：匯出 Q&A 時包含學生回答 ===========
    async def export_qas_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None
    ) -> str:
        """
        匯出 Q&A 資料為 CSV 格式 (包含學生在限時互動期間的作答)
        """
        database = db.get_db()
        qa_collection = database["qas"]
        question_collection = database["questions"] # 引入 questions 表來撈取學生作答
        
        query: Dict[str, Any] = {"course_id": course_id}
        if class_id:
            query["$or"] = [{"class_id": class_id}, {"class_id": None}]
        
        cursor = qa_collection.find(query).sort("created_at", -1)
        qas = await cursor.to_list(length=None)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 🔥 修改標題列，移除用處不大的「相關提問數量」，新增「學生回覆內容」
        writer.writerow([
            "Q&A ID", "問題", "標準答案", "分類", "標籤", "是否發布",
            "發布時間", "建立者", "建立時間", "學生回覆內容" 
        ])
        
        for qa in qas:
            qa_id_str = str(qa["_id"])
            tags = qa.get("tags") or []
            
            # 🔥 去 questions 集合中尋找針對此 Q&A 的學生回覆
            replies_cursor = question_collection.find({"reply_to_qa_id": qa_id_str}).sort("created_at", 1)
            replies = await replies_cursor.to_list(length=None)
            
            # 將學生的回覆組合成單一字串排版
            formatted_replies = []
            for r in replies:
                r_time = r.get("created_at")
                r_time_str = format_datetime(r_time) if r_time else ""
                r_pseudo = r.get("pseudonym", "匿名")
                
                # 將換行符號替換掉，避免 CSV 排版大亂
                r_text = str(r.get("question_text", "")).replace('\n', ' ').replace('\r', '')
                
                formatted_replies.append(f"[{r_pseudo} {r_time_str}] {r_text}")
                
            # 若無人回覆則顯示提示
            replies_str = "\n".join(formatted_replies) if formatted_replies else "無學生回覆"

            writer.writerow([
                qa_id_str,
                qa.get("question", ""),
                qa.get("answer", ""),
                qa.get("category", ""),
                ", ".join(tags),
                "是" if qa.get("is_published", False) else "否",
                format_datetime(qa.get("publish_date")) if qa.get("publish_date") else "",
                qa.get("created_by", ""),
                format_datetime(qa.get("created_at")) if qa.get("created_at") else "",
                replies_str # 🔥 將組合好的回覆字串塞入最後一個欄位
            ])
        
        csv_content = output.getvalue()
        output.close()
        return csv_content
    # ==========================================================

    async def export_statistics_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None
    ) -> str:
        """
        匯出統計資料為 CSV 格式
        """
        database = db.get_db()
        collection = database["questions"]
        
        query: Dict[str, Any] = {"course_id": course_id, "status": {"$ne": "DELETED"}}
        if class_id:
            query["class_id"] = class_id
        
        # 1. 統計各狀態
        status_pipeline = [
            {"$match": query},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_stats = await collection.aggregate(status_pipeline).to_list(length=None)
        
        # 2. 統計難度分布
        difficulty_pipeline = [
            {"$match": {**query, "difficulty_level": {"$ne": None}}},
            {"$group": {"_id": {"$toUpper": "$difficulty_level"}, "count": {"$sum": 1}}}
        ]
        difficulty_stats = await collection.aggregate(difficulty_pipeline).to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["=== 提問狀態統計 ==="])
        writer.writerow(["狀態", "數量"])
        for stat in status_stats:
            writer.writerow([stat["_id"], stat["count"]])
        writer.writerow([])
        
        writer.writerow(["=== 難度分布統計 ==="])
        writer.writerow(["難度等級", "數量"])
        for stat in difficulty_stats:
            writer.writerow([stat["_id"], stat["count"]])
        
        csv_content = output.getvalue()
        output.close()
        return csv_content


# 全域服務實例
export_service = ExportService()