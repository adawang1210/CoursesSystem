"""
資料匯出服務
提供 CSV 格式的統計資料與作答明細匯出功能
"""
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..database import db
from ..utils.datetime_helper import format_datetime, build_date_range_query


class ExportService:
    """資料匯出服務類別"""
    
    async def export_questions_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None,
        cluster_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        qa_id: Optional[str] = None
    ) -> str:
        """
        匯出學生作答明細資料為 CSV 格式 (包含 AI 分析欄位)
        """
        database = db.get_db()
        collection = database["questions"]
        
        query: Dict[str, Any] = {"course_id": course_id}
        
        if qa_id:
            query["reply_to_qa_id"] = qa_id
        
        if class_id:
            query["class_id"] = class_id

        if cluster_id:
            query["cluster_id"] = cluster_id
        
        # 時間區間過濾
        query.update(build_date_range_query(start_date, end_date))
        
        # 取得資料
        cursor = collection.find(query).sort("created_at", -1)
        questions = await cursor.to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 預先查詢 cluster 名稱對照表
        cluster_ids = list(set(q.get("cluster_id") for q in questions if q.get("cluster_id")))
        cluster_names = {}
        if cluster_ids:
            from bson import ObjectId as ObjId
            valid_ids = [ObjId(cid) for cid in cluster_ids if cid]
            if valid_ids:
                clusters_cursor = database["clusters"].find({"_id": {"$in": valid_ids}})
                async for c in clusters_cursor:
                    cluster_names[str(c["_id"])] = c.get("topic_label", "")
        
        writer.writerow([
            "學號", "學生作答內容", "批閱狀態", "老師評語",
            "AI 分群名稱", "作答時間"
        ])
        
        for q in questions:
            status = q.get("review_status", "pending")
            status_label = {"pending": "待批閱", "approved": "通過", "rejected": "退回"}.get(status, status)
            cluster_id = q.get("cluster_id", "")
            cluster_label = cluster_names.get(cluster_id, "") if cluster_id else ""
            
            writer.writerow([
                q.get("student_id", "") or "",
                q.get("question_text", ""),
                status_label,
                q.get("feedback", "") or "",
                cluster_label,
                format_datetime(q.get("created_at")) if q.get("created_at") else ""
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
            "包含回覆數", "平均難度", "關鍵字", "是否人工鎖定"
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


    async def export_qas_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None,
        start_date: Optional[datetime] = None, # 🔥 新增時間參數
        end_date: Optional[datetime] = None    # 🔥 新增時間參數
    ) -> str:
        """
        匯出 Q&A 任務資料為 CSV 格式 (包含學生作答紀錄)
        """
        database = db.get_db()
        qa_collection = database["qas"]
        question_collection = database["questions"] 
        
        query: Dict[str, Any] = {"course_id": course_id}
        if class_id:
            query["$or"] = [{"class_id": class_id}, {"class_id": None}]

        query.update(build_date_range_query(start_date, end_date))
        
        cursor = qa_collection.find(query).sort("created_at", -1)
        qas = await cursor.to_list(length=None)
        
        # Batch query all replies for all QAs
        qa_ids = [str(qa["_id"]) for qa in qas]
        all_replies_cursor = question_collection.find(
            {"reply_to_qa_id": {"$in": qa_ids}}
        ).sort("created_at", 1)
        all_replies = await all_replies_cursor.to_list(length=None)
        
        replies_map = {}
        for r in all_replies:
            qa_id = r.get("reply_to_qa_id")
            replies_map.setdefault(qa_id, []).append(r)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "任務 ID", "任務問題", "標準答案/批閱基準", "分類", "標籤", "是否發布",
            "發布時間", "建立者", "建立時間", "學生回覆內容" 
        ])
        
        for qa in qas:
            qa_id_str = str(qa["_id"])
            tags = qa.get("tags") or []
            
            # Use pre-fetched replies from map
            replies = replies_map.get(qa_id_str, [])
            
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
                replies_str 
            ])
        
        csv_content = output.getvalue()
        output.close()
        return csv_content


    async def export_statistics_to_csv(
        self,
        course_id: str,
        class_id: Optional[str] = None,
        start_date: Optional[datetime] = None, # 🔥 新增時間參數
        end_date: Optional[datetime] = None    # 🔥 新增時間參數
    ) -> str:
        """
        匯出任務成效統計資料為 CSV 格式
        """
        database = db.get_db()
        collection = database["questions"]
        
        query: Dict[str, Any] = {"course_id": course_id}
        if class_id:
            query["class_id"] = class_id

        query.update(build_date_range_query(start_date, end_date))
        
        # 1. 取得總作答數
        total_replies = await collection.count_documents(query)
        
        # 2. 統計難度分布
        difficulty_pipeline = [
            {"$match": {**query, "difficulty_level": {"$ne": None}}},
            {"$group": {"_id": {"$toUpper": "$difficulty_level"}, "count": {"$sum": 1}}}
        ]
        difficulty_stats = await collection.aggregate(difficulty_pipeline).to_list(length=None)
        
        # 建立 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["=== 任務作答總覽 ==="])
        writer.writerow(["總收集回覆數", total_replies])
        writer.writerow([])
        
        writer.writerow(["=== 學生學習難度分布 ==="])
        writer.writerow(["難度等級", "數量"])
        for stat in difficulty_stats:
            diff_label = stat["_id"]
            if diff_label == "EASY": diff_label = "簡單"
            elif diff_label == "MEDIUM": diff_label = "中等"
            elif diff_label == "HARD": diff_label = "困難"
            
            writer.writerow([diff_label, stat["count"]])
        
        csv_content = output.getvalue()
        output.close()
        return csv_content


# 全域服務實例
export_service = ExportService()