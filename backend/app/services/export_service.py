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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        匯出提問資料為 CSV 格式
        
        Args:
            course_id: 課程ID
            class_id: 班級ID (可選)
            start_date: 開始日期 (可選)
            end_date: 結束日期 (可選)
        
        Returns:
            CSV 格式的字串
        """
        database = db.get_db()
        collection = database["questions"]
        
        # 建立查詢條件
        query: Dict[str, Any] = {"course_id": course_id}
        
        if class_id:
            query["class_id"] = class_id
        
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
            "提問ID",
            "去識別化代號",
            "提問內容",
            "狀態",
            "AI聚類ID",
            "難度分數",
            "難度等級",
            "關鍵字",
            "是否已合併",
            "合併至Q&A ID",
            "建立時間",
            "更新時間"
        ])
        
        # 寫入資料列
        for q in questions:
            writer.writerow([
                str(q["_id"]),
                q.get("pseudonym", ""),
                q.get("question_text", ""),
                q.get("status", ""),
                q.get("cluster_id", ""),
                q.get("difficulty_score", ""),
                q.get("difficulty_level", ""),
                ", ".join(q.get("keywords", [])),
                "是" if q.get("is_merged", False) else "否",
                q.get("merged_to_qa_id", ""),
                format_datetime(q.get("created_at")),
                format_datetime(q.get("updated_at"))
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    async def export_qas_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None
    ) -> str:
        """
        匯出 Q&A 資料為 CSV 格式
        
        Args:
            course_id: 課程ID
            class_id: 班級ID (可選)
        
        Returns:
            CSV 格式的字串
        """
        database = db.get_db()
        collection = database["qas"]
        
        # 建立查詢條件
        query: Dict[str, Any] = {"course_id": course_id}
        
        if class_id:
            query["$or"] = [
                {"class_id": class_id},
                {"class_id": None}
            ]
        
        # 取得資料
        cursor = collection.find(query).sort("created_at", -1)
        qas = await cursor.to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 寫入標題列
        writer.writerow([
            "Q&A ID",
            "問題",
            "回答",
            "分類",
            "標籤",
            "是否發布",
            "發布時間",
            "相關提問數量",
            "建立者",
            "建立時間"
        ])
        
        # 寫入資料列
        for qa in qas:
            writer.writerow([
                str(qa["_id"]),
                qa.get("question", ""),
                qa.get("answer", ""),
                qa.get("category", ""),
                ", ".join(qa.get("tags", [])),
                "是" if qa.get("is_published", False) else "否",
                format_datetime(qa.get("publish_date")),
                len(qa.get("related_question_ids", [])),
                qa.get("created_by", ""),
                format_datetime(qa.get("created_at"))
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content
    
    async def export_statistics_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None
    ) -> str:
        """
        匯出統計資料為 CSV 格式
        
        包含：
        - 各狀態的提問數量統計
        - 各聚類的提問數量統計
        - 難度分布統計
        
        Args:
            course_id: 課程ID
            class_id: 班級ID (可選)
        
        Returns:
            CSV 格式的字串
        """
        database = db.get_db()
        collection = database["questions"]
        
        # 建立查詢條件
        query: Dict[str, Any] = {"course_id": course_id}
        if class_id:
            query["class_id"] = class_id
        
        # 統計各狀態的提問數量
        status_pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        status_stats = await collection.aggregate(status_pipeline).to_list(length=None)
        
        # 統計各聚類的提問數量
        cluster_pipeline = [
            {"$match": {**query, "cluster_id": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$cluster_id",
                    "count": {"$sum": 1},
                    "avg_difficulty": {"$avg": "$difficulty_score"}
                }
            },
            {"$sort": {"count": -1}}
        ]
        cluster_stats = await collection.aggregate(cluster_pipeline).to_list(length=None)
        
        # 統計難度分布
        difficulty_pipeline = [
            {"$match": {**query, "difficulty_level": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$difficulty_level",
                    "count": {"$sum": 1}
                }
            }
        ]
        difficulty_stats = await collection.aggregate(difficulty_pipeline).to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 第一部分：狀態統計
        writer.writerow(["=== 提問狀態統計 ==="])
        writer.writerow(["狀態", "數量"])
        for stat in status_stats:
            writer.writerow([stat["_id"], stat["count"]])
        writer.writerow([])
        
        # 第二部分：聚類統計
        writer.writerow(["=== AI 聚類統計 ==="])
        writer.writerow(["聚類ID", "提問數量", "平均難度"])
        for stat in cluster_stats:
            writer.writerow([
                stat["_id"],
                stat["count"],
                f"{stat.get('avg_difficulty', 0):.2f}"
            ])
        writer.writerow([])
        
        # 第三部分：難度分布統計
        writer.writerow(["=== 難度分布統計 ==="])
        writer.writerow(["難度等級", "數量"])
        for stat in difficulty_stats:
            writer.writerow([stat["_id"], stat["count"]])
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content


# 全域服務實例
export_service = ExportService()

