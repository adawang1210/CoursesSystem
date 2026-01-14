"""
AI 層整合 API
提供 AI/NLP 服務調用的專用接口
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from ..models.schemas import AIAnalysisRequest, AIAnalysisResult, Cluster
from ..services.question_service import question_service
from ..services.ai_service import ai_service


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

@router.post("/questions/{question_id}/draft", summary="生成/重寫問題的回覆草稿")
async def generate_response_draft(
    question_id: str,
    background_tasks: BackgroundTasks
):
    """
    觸發 AI 為特定問題生成回覆草稿
    """
    # 1. 取得問題資料
    question = await question_service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="找不到此提問")

    # 2. 定義背景任務函數
    async def _generate_and_save_draft(qid: str, text: str):
        try:
            # 呼叫 AI 生成草稿
            draft = await ai_service.generate_response_draft(text)
            
            # 呼叫 AI 生成摘要 (順便做)
            analysis = await ai_service.analyze_question(text)
            summary = analysis.get("summary", "")
            
            # 構造更新物件 (利用現有的 update_ai_analysis 介面)
            # 注意：這裡假設您已經在 schemas.py 的 AIAnalysisResult 加入了 response_draft 欄位
            result = AIAnalysisResult(
                question_id=qid,
                difficulty_score=question.get("difficulty_score", 0.5), # 保持原值
                keywords=question.get("keywords", []), # 保持原值
                cluster_id=question.get("cluster_id"), # 保持原值
                response_draft=draft,    # <--- 更新重點
                summary=summary          # <--- 更新重點
            )
            
            await question_service.update_ai_analysis(qid, result)
            print(f"✅ 已為問題 {qid} 生成草稿")
            
        except Exception as e:
            print(f"❌ 草稿生成失敗: {str(e)}")

    # 3. 加入背景任務 (讓 API 立刻回應，不用等 AI)
    background_tasks.add_task(
        _generate_and_save_draft, 
        question_id, 
        question["question_text"]
    )

    return {
        "success": True,
        "message": "已開始生成草稿，請稍後重新整理頁面查看"
    }


@router.post("/clusters/generate", summary="執行課程主題聚類分析")
async def generate_course_clusters(
    course_id: str,
    background_tasks: BackgroundTasks
):
    """
    分析該課程所有「未歸類」的問題，嘗試進行自動分群與命名
    """
    # 定義背景任務
    async def _run_clustering_task(cid: str):
        print(f"🤖 開始執行課程 {cid} 的聚類分析...")
        try:
            # 1. 撈出該課程所有還沒分群的問題 (Pending + Cluster=None)
            questions = await question_service.get_pending_questions_for_ai(cid, limit=50)
            
            if not questions:
                print("沒有需要分群的問題")
                return

            # 簡化版邏輯：直接把前 10 個問題丟給 AI 請它歸納一個主題
            # (實務上這裡可以用 K-Means 或更複雜的邏輯，但先從簡單的開始)
            q_texts = [q['question_text'] for q in questions]
            
            # 呼叫 AI 歸納主題
            cluster_result = await ai_service.generate_cluster_label(q_texts)
            
            topic_label = cluster_result.get("topic_label", "未命名主題")
            summary = cluster_result.get("summary", "")
            
            print(f"🔍 AI 歸納出的主題: {topic_label}")
            
            # TODO: 這裡應該要呼叫 service 把這些問題的 cluster_id 更新
            # 並且建立一個新的 Cluster Document
            # (這部分邏輯較複雜，建議先實作到這裡確認 AI 能跑)
            
        except Exception as e:
            print(f"❌ 聚類分析失敗: {str(e)}")

    background_tasks.add_task(_run_clustering_task, course_id)

    return {
        "success": True,
        "message": "聚類分析任務已啟動"
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

