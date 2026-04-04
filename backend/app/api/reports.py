"""
報表匯出與統計 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from datetime import datetime
from ..services.export_service import export_service
from ..database import db  

router = APIRouter(prefix="/reports", tags=["reports"])

# ==========================================
# 📊 第一部分：前端圖表用的 JSON 統計資料 API
# ==========================================

@router.get("/statistics", summary="取得課程統計摘要 (圖表用)")
async def get_statistics(course_id: str = Query(..., description="課程ID")):
    """
    供前端統計儀表板 (Dashboard) 使用的聚合資料
    包含總作答數、平均難度與難度分佈
    """
    try:
        database = db.get_db()
        questions_coll = database["questions"]
        
        # =========== 🔥 修正：只撈取有綁定 Q&A 任務的有效作答 ===========
        base_query = {
            "course_id": course_id, 
            "reply_to_qa_id": {"$ne": None} # 過濾掉舊版一般提問
        }
        # ==============================================================
        
        # 1. 基本計數
        total = await questions_coll.count_documents(base_query)
        
        # 2. 難度分布與平均難度分數
        diff_pipeline = [
            {"$match": base_query},
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
                "avg_difficulty_score": avg_difficulty,
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
        
        # =========== 🔥 修正：只撈取有綁定 Q&A 任務的聚類群組 ===========
        cursor = clusters_coll.find({
            "course_id": course_id,
            "qa_id": {"$ne": None} # 過濾掉舊版一般提問的聚類
        }).sort("question_count", -1).limit(10)
        # ==============================================================
        
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
    qa_id: Optional[str] = Query(None, description="Q&A 任務ID"),
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
            start_date=start_dt, end_date=end_dt, qa_id=qa_id
        )
        
        # 用課程名稱和日期命名
        database = db.get_db()
        course = await database["courses"].find_one({"_id": __import__("bson").ObjectId(course_id)})
        course_name = course["course_name"] if course else course_id
        qa_label = ""
        if qa_id:
            qa_doc = await database["qas"].find_one({"_id": __import__("bson").ObjectId(qa_id)})
            if qa_doc:
                q_text = qa_doc.get("question", "")[:20]
                qa_label = f"_{q_text}"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{course_name}{qa_label}_作答明細_{timestamp}.csv"
        
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse', fromlist=['quote']).quote(filename)}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/clusters", summary="匯出 AI 主題分析報表 CSV")
async def export_clusters_csv(course_id: str = Query(..., description="課程ID")):
    try:
        csv_content = await export_service.export_clusters_to_csv(course_id=course_id)
        database = db.get_db()
        course = await database["courses"].find_one({"_id": __import__("bson").ObjectId(course_id)})
        course_name = course["course_name"] if course else course_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{course_name}_AI批閱分析_{timestamp}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse', fromlist=['quote']).quote(filename)}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/qas", summary="匯出 Q&A 資料 CSV")
async def export_qas_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    start_date: Optional[datetime] = Query(None, description="開始日期"), 
    end_date: Optional[datetime] = Query(None, description="結束日期")    
):
    try:
        csv_content = await export_service.export_qas_to_csv(course_id, class_id, start_date, end_date)
        database = db.get_db()
        course = await database["courses"].find_one({"_id": __import__("bson").ObjectId(course_id)})
        course_name = course["course_name"] if course else course_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{course_name}_QA紀錄_{timestamp}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse', fromlist=['quote']).quote(filename)}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/statistics", summary="匯出統計資料 CSV")
async def export_statistics_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    start_date: Optional[datetime] = Query(None, description="開始日期"), 
    end_date: Optional[datetime] = Query(None, description="結束日期")    
):
    try:
        csv_content = await export_service.export_statistics_to_csv(course_id, class_id, start_date, end_date)
        database = db.get_db()
        course = await database["courses"].find_one({"_id": __import__("bson").ObjectId(course_id)})
        course_name = course["course_name"] if course else course_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"{course_name}_成效統計_{timestamp}.csv"
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{__import__('urllib.parse', fromlist=['quote']).quote(filename)}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")