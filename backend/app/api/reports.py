"""
報表匯出與統計 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from datetime import datetime
from ..services.export_service import export_service
from ..database import db  # 🔥 新增：為了能在 API 中直接查詢資料庫進行統計

router = APIRouter(prefix="/reports", tags=["reports"])

# ==========================================
# 📊 第一部分：前端圖表用的 JSON 統計資料 API
# ==========================================

@router.get("/statistics", summary="取得課程統計摘要 (圖表用)")
async def get_statistics(course_id: str = Query(..., description="課程ID")):
    """
    供前端統計儀表板 (Dashboard) 使用的聚合資料
    包含總提問數、各狀態數量、平均難度等
    """
    try:
        database = db.get_db()
        questions_coll = database["questions"]
        
        # 1. 基本計數
        total = await questions_coll.count_documents({"course_id": course_id, "status": {"$ne": "DELETED"}})
        pending = await questions_coll.count_documents({"course_id": course_id, "status": "PENDING"})
        approved = await questions_coll.count_documents({"course_id": course_id, "status": "APPROVED"})
        
        # 2. 狀態分布
        status_pipeline = [
            {"$match": {"course_id": course_id, "status": {"$ne": "DELETED"}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_dist = {}
        async for doc in questions_coll.aggregate(status_pipeline):
            status_dist[doc["_id"]] = doc["count"]
            
        # 3. 難度分布與平均難度分數
        diff_pipeline = [
            {"$match": {"course_id": course_id, "status": {"$ne": "DELETED"}}},
            {"$group": {
                "_id": {"$toUpper": "$difficulty_level"},
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$difficulty_score"}
            }}
        ]
        
        difficulty_dist = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
        total_score = 0
        scored_count = 0
        
        async for doc in questions_coll.aggregate(diff_pipeline):
            level = doc["_id"] if doc["_id"] else "UNKNOWN"
            if level in difficulty_dist:
                difficulty_dist[level] = doc["count"]
            
            # 計算全班平均難度分數
            if doc.get("avg_score") is not None:
                total_score += doc["avg_score"] * doc["count"]
                scored_count += doc["count"]
                
        avg_difficulty = (total_score / scored_count) if scored_count > 0 else 0
        
        return {
            "success": True,
            "data": {
                "total_questions": total,
                "pending_questions": pending,
                "approved_questions": approved,
                "avg_difficulty_score": avg_difficulty,
                "status_distribution": status_dist,
                "difficulty_distribution": {
                    "easy": difficulty_dist["EASY"],
                    "medium": difficulty_dist["MEDIUM"],
                    "hard": difficulty_dist["HARD"]
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得統計資料失敗: {str(e)}")


@router.get("/clusters/summary", summary="取得課程聚類摘要 (圖表用)")
async def get_clusters_summary(course_id: str = Query(..., description="課程ID")):
    """
    供前端統計儀表板繪製熱門主題圖表使用
    """
    try:
        database = db.get_db()
        clusters_coll = database["clusters"]
        
        # 取出該課程底下，包含最多問題的前 10 個主題
        cursor = clusters_coll.find({"course_id": course_id}).sort("question_count", -1).limit(10)
        clusters = await cursor.to_list(length=10)
        
        for c in clusters:
            c["_id"] = str(c["_id"])
            
        return {
            "success": True,
            "data": clusters
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得主題摘要失敗: {str(e)}")


# ==========================================
# 📥 第二部分：CSV 檔案匯出 API
# ==========================================

@router.get("/export/questions", summary="匯出提問資料 CSV")
async def export_questions_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    cluster_id: Optional[str] = Query(None, description="聚類ID (篩選特定主題)"),
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)")
):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        csv_content = await export_service.export_questions_to_csv(
            course_id=course_id, class_id=class_id, cluster_id=cluster_id, 
            start_date=start_dt, end_date=end_dt
        )
        
        filename = f"questions_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/clusters", summary="匯出 AI 主題分析報表 CSV")
async def export_clusters_csv(course_id: str = Query(..., description="課程ID")):
    try:
        csv_content = await export_service.export_clusters_to_csv(course_id=course_id)
        filename = f"clusters_analysis_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/qas", summary="匯出 Q&A 資料 CSV")
async def export_qas_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    try:
        csv_content = await export_service.export_qas_to_csv(course_id=course_id, class_id=class_id)
        filename = f"qas_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/statistics", summary="匯出統計資料 CSV")
async def export_statistics_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    try:
        csv_content = await export_service.export_statistics_to_csv(course_id=course_id, class_id=class_id)
        filename = f"statistics_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")