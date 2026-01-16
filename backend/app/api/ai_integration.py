"""
AI 層整合 API
提供 AI/NLP 服務調用的專用接口
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from bson import ObjectId
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
            draft = ai_service.generate_response_draft(text)
            
            # 呼叫 AI 生成摘要 (順便做)
            analysis = ai_service.analyze_question(text)
            summary = analysis.get("summary", "")

            new_difficulty = analysis.get("difficulty_score")
            if new_difficulty is None:
                # 嘗試讀取舊資料，如果舊資料也是 None，就給 0.5
                old_diff = question.get("difficulty_score")
                new_difficulty = old_diff if old_diff is not None else 0.5

            new_keywords = analysis.get("keywords")
            if new_keywords is None:
                 new_keywords = question.get("keywords") or []
            
            # 構造更新物件 (利用現有的 update_ai_analysis 介面)
            # 注意：這裡假設您已經在 schemas.py 的 AIAnalysisResult 加入了 response_draft 欄位
            result = AIAnalysisResult(
                question_id=qid,
                difficulty_score=float(new_difficulty), # 保持原值
                keywords=new_keywords, # 保持原值
                cluster_id=question.get("cluster_id"), # 保持原值
                response_draft=draft,    # <--- 更新重點
                summary=summary          # <--- 更新重點
            )
            
            await question_service.update_ai_analysis(qid, result)
            print(f"✅ 已為問題 {qid} 生成草稿")
            
        except Exception as e:
            print(f"❌ 草稿生成失敗: {str(e)}")
            import traceback
            traceback.print_exc()

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
        print(f"🤖 [升級版] 開始執行課程 {cid} 的多維聚類分析...")
        from ..database import db
        from bson import ObjectId
        from datetime import datetime
        
        try:
            # 1. 撈出待處理問題
            questions = await question_service.get_pending_questions_for_ai(cid, limit=50)
            if not questions:
                print("沒有需要分群的問題")
                return

            q_texts = [q['question_text'] for q in questions]
            
            # 🔥 修改點：改呼叫新的分群方法
            # (請確認 ai_service 已經有 perform_advanced_clustering 方法)
            ai_result = ai_service.perform_advanced_clustering(q_texts)
            
            # 防呆：確保回傳結構正確
            if not ai_result or "clusters" not in ai_result:
                print("❌ AI 回傳格式錯誤，無法分群")
                return

            clusters_data = ai_result.get("clusters", [])
            print(f"📊 AI 將問題分成了 {len(clusters_data)} 個群組")
            
            database = db.get_db()
            
            # 2. 遍歷 AI 分好的每一個群組
            for cluster_data in clusters_data:
                topic_label = cluster_data.get("topic_label", "未命名群組")
                indices = cluster_data.get("question_indices", []) # 這是 [0, 1, 4...]
                
                if not indices:
                    continue
                    
                print(f"  📂 處理群組: {topic_label} (包含 {len(indices)} 題)")
                
                # A. 建立 Cluster 文件
                new_cluster_id = ObjectId()
                new_cluster_doc = {
                    "_id": new_cluster_id,
                    "course_id": cid, # 這裡假設 cid 是 string
                    "topic_label": topic_label,
                    "summary": cluster_data.get("summary", ""),
                    "keywords": [], 
                    "question_count": len(indices),
                    "avg_difficulty": 0.0, 
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                await database["clusters"].insert_one(new_cluster_doc)
                
                # B. 找出這個群組對應的 Question IDs
                # 因為 AI 回傳的是 index (0, 1, 2...)，我們要映射回 questions 陣列裡的 _id
                target_q_ids = []
                for idx in indices:
                    # 防呆：確保 index 沒有超出範圍
                    if isinstance(idx, int) and 0 <= idx < len(questions):
                        target_q_ids.append(ObjectId(questions[idx]['_id']))
                
                # C. 批次更新這些問題的 cluster_id
                if target_q_ids:
                    await database["questions"].update_many(
                        {"_id": {"$in": target_q_ids}},
                        {"$set": {
                            "cluster_id": str(new_cluster_id),
                            "updated_at": datetime.utcnow()
                        }}
                    )

            print(f"✅ 多維聚類分析完成！")
            
        except Exception as e:
            print(f"❌ 聚類分析失敗: {str(e)}")
            import traceback
            traceback.print_exc()

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

    # 1. 查詢條件：同時支援 String 與 ObjectId 格式的 course_id
    match_condition = {
        "$or": [
            {"course_id": course_id},               
            {"course_id": ObjectId(course_id)}      
        ],
        "cluster_id": {"$ne": None}                 
    }
    
    pipeline = [
        {"$match": match_condition},
        {"$group": {
            "_id": "$cluster_id",
            "count": {"$sum": 1},
            # 注意：如果資料庫沒有 difficulty_score 欄位，這裡會是 null
            "avg_difficulty": {"$avg": "$difficulty_score"},
            # 🔥 修正 1：必須把關鍵字收集起來，下面的迴圈才讀得到
            "keywords": {"$push": "$keywords"} 
        }}
    ]
    
    results = await collection.aggregate(pipeline).to_list(length=None)

    clusters_collection = database["clusters"]
    
    clusters = []
    for result in results:
        # 2. 處理關鍵字：從 questions 聚合結果計算 Top 5
        all_keywords = []
        # 加上防呆，確保 keywords 存在且是列表
        raw_keywords = result.get("keywords", [])
        for kw_list in raw_keywords:
            if isinstance(kw_list, list):
                all_keywords.extend(kw_list)
        
        # 統計頻率
        keyword_freq = {}
        for kw in all_keywords:
            if kw: # 排除空字串
                keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        
        # 取前 5 個
        top_keywords = sorted(
            keyword_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # 3. 取得 Cluster 詳細資訊 (Topic Label)
        topic_label = "未命名主題"
        try:
            cluster_oid = ObjectId(result["_id"])
            cluster_info = await clusters_collection.find_one({"_id": cluster_oid})
            if cluster_info:
                topic_label = cluster_info.get("topic_label", "未命名主題")
        except:
            pass # ID 格式錯誤或其他問題則忽略
            
        # 🔥 修正 2：確保 avg_difficulty 絕對不是 None
        # 如果是 None，則強制轉為 0，避免前端 toFixed 報錯
        avg_diff = result.get("avg_difficulty")
        if avg_diff is None:
            avg_diff = 0.0

        clusters.append({
            "cluster_id": str(result["_id"]),
            "topic_label": topic_label,
            "question_count": result["count"],
            "avg_difficulty": avg_diff, # 這裡傳出去的一定是數字
            "top_keywords": [kw[0] for kw in top_keywords]
        })
    
    return {
        "success": True,
        "data": clusters,
        "total_clusters": len(clusters)
    }

