"""
AI 層整合 API
提供 AI/NLP 服務調用的專用接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from ..models.schemas import AIAnalysisRequest, AIAnalysisResult
from ..services.question_service import question_service


router = APIRouter(prefix="/ai", tags=["ai-integration"])


@router.get("/questions/pending", response_model=dict, summary="取得待 AI 分析的提問")
async def get_pending_questions_for_ai(
    course_id: str = Query(..., description="課程ID"),
    limit: int = Query(100, ge=1, le=500, description="限制筆數")
):
    """
    取得待 AI 分析的提問列表
    
    **此 API 僅返回去識別化後的資料**：
    - pseudonym (去識別化代號)
    - question_text (提問內容)
    - 不包含任何可識別個人身份的資訊
    
    **由 AI/NLP 服務定期調用**
    """
    questions = await question_service.get_pending_questions_for_ai(
        course_id, limit
    )
    
    return {
        "success": True,
        "data": questions,
        "total": len(questions)
    }


@router.post("/analysis/batch", response_model=dict, summary="批次寫入 AI 分析結果")
async def batch_update_ai_analysis(
    results: List[AIAnalysisResult]
):
    """
    批次寫入 AI 分析結果
    
    **此 API 由 AI/NLP 服務調用**
    
    接收 AI 分析結果並更新至資料庫：
    - cluster_id: AI 聚類ID
    - difficulty_score: 難度分數 (0-1)
    - keywords: 關鍵字列表
    """
    success_count = 0
    failed_count = 0
    errors = []
    
    for result in results:
        try:
            question = await question_service.update_ai_analysis(
                result.question_id,
                result
            )
            if question:
                success_count += 1
            else:
                failed_count += 1
                errors.append({
                    "question_id": result.question_id,
                    "error": "找不到此提問"
                })
        except Exception as e:
            failed_count += 1
            errors.append({
                "question_id": result.question_id,
                "error": str(e)
            })
    
    return {
        "success": True,
        "message": f"成功更新 {success_count} 筆，失敗 {failed_count} 筆",
        "success_count": success_count,
        "failed_count": failed_count,
        "errors": errors if errors else None
    }


@router.post("/analysis/single", response_model=dict, summary="單筆寫入 AI 分析結果")
async def single_update_ai_analysis(
    result: AIAnalysisResult
):
    """
    單筆寫入 AI 分析結果
    
    **此 API 由 AI/NLP 服務調用**
    """
    question = await question_service.update_ai_analysis(
        result.question_id,
        result
    )
    
    if not question:
        raise HTTPException(status_code=404, detail="找不到此提問")
    
    return {
        "success": True,
        "message": "AI 分析結果更新成功",
        "data": question
    }


@router.get("/clusters/{course_id}", response_model=dict, summary="取得課程的所有聚類")
async def get_clusters_summary(course_id: str):
    """
    取得課程的所有 AI 聚類摘要
    
    返回每個聚類的：
    - cluster_id
    - 提問數量
    - 平均難度
    - 代表性關鍵字
    """
    from ..database import db
    
    database = db.get_db()
    collection = database["questions"]
    
    pipeline = [
        {
            "$match": {
                "course_id": course_id,
                "cluster_id": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$cluster_id",
                "count": {"$sum": 1},
                "avg_difficulty": {"$avg": "$difficulty_score"},
                "keywords": {"$push": "$keywords"}
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]
    
    results = await collection.aggregate(pipeline).to_list(length=None)
    
    # 處理關鍵字：展平並統計頻率
    clusters = []
    for result in results:
        all_keywords = []
        for kw_list in result["keywords"]:
            all_keywords.extend(kw_list)
        
        # 統計關鍵字頻率
        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        
        # 取前 5 個最常見的關鍵字
        top_keywords = sorted(
            keyword_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        clusters.append({
            "cluster_id": result["_id"],
            "question_count": result["count"],
            "avg_difficulty": result.get("avg_difficulty", 0),
            "top_keywords": [kw[0] for kw in top_keywords]
        })
    
    return {
        "success": True,
        "data": clusters,
        "total_clusters": len(clusters)
    }

