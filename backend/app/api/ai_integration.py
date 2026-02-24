"""
AI 層整合 API
提供 AI/NLP 服務調用的專用接口
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel  # 🔥 新增這行引入 BaseModel
from ..models.schemas import (
    AIAnalysisRequest, 
    AIAnalysisResult, 
    ClusterGenerateRequest, # 確保也有引入這個
    ClusterUpdate           # 🔥 請確認引入的是這個名稱
)
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
    request: ClusterGenerateRequest,  # 🔥 修改 1：改用 Pydantic Model 接收 JSON Body
    background_tasks: BackgroundTasks
):
    """
    分析該課程所有「未歸類」的問題，嘗試進行自動分群與命名
    """
    course_id = request.course_id
    max_clusters = request.max_clusters

    # 定義背景任務
    async def _run_clustering_task(cid: str, max_c: int):
        print(f"🤖 [智能歸檔模式] 開始分析課程 {cid} (總上限 {max_c} 組)...")
        from ..database import db
        from bson import ObjectId
        from datetime import datetime
        
        try:
            database = db.get_db()

            # -------------------------------------------------------
            # 🔥 步驟 1: 先撈出「現有的」聚類標籤 (Context)
            # -------------------------------------------------------
            existing_clusters_cursor = database["clusters"].find({"course_id": cid})
            existing_clusters = await existing_clusters_cursor.to_list(length=None)
            
            # 建立查表字典
            existing_topic_map = {c["topic_label"]: c["_id"] for c in existing_clusters}
            existing_topic_names = list(existing_topic_map.keys())
            
            # 🔥 關鍵修改：計算「剩餘額度」
            current_count = len(existing_topic_names)
            remaining_quota = max_c - current_count
            
            # 若既有分類已超過或等於上限，則不允許新增 (或設為 0)
            if remaining_quota < 0:
                remaining_quota = 0
                
            print(f"📚 狀態: 既有 {current_count} 組 | 上限 {max_c} 組 | 💡 可新增 {remaining_quota} 組")

            # -------------------------------------------------------
            # 🔥 步驟 2: 撈出「未分類」的問題
            # -------------------------------------------------------
            questions = await question_service.get_pending_questions_for_ai(cid, limit=50)
            
            if not questions:
                print("✅ 沒有新的未分類問題，工作結束")
                return

            q_texts = [q['question_text'] for q in questions]
            
            # -------------------------------------------------------
            # 🔥 步驟 3: 呼叫 AI (傳入計算後的額度)
            # -------------------------------------------------------
            # 注意：這裡的參數名稱必須與 ai_service.py 定義的一致 (max_new_topics)
            ai_result = ai_service.perform_advanced_clustering(
                q_texts, 
                max_new_topics=remaining_quota,  # <--- 改用這個參數
                existing_topics=existing_topic_names
            )
            
            if not ai_result or "clusters" not in ai_result:
                print("❌ AI 回傳格式錯誤")
                return

            clusters_data = ai_result.get("clusters", [])
            print(f"📊 AI 將 {len(q_texts)} 個新問題分成了 {len(clusters_data)} 組")

            # -------------------------------------------------------
            # 🔥 步驟 4: 智慧寫入 (比對新舊)
            # -------------------------------------------------------
            # (這部分的邏輯保持不變，負責將 AI 結果寫入資料庫)
            for cluster_data in clusters_data:
                topic_label = cluster_data.get("topic_label", "未命名群組")
                indices = cluster_data.get("question_indices", [])
                
                if not indices:
                    continue
                
                if topic_label in existing_topic_map:
                    # 歸入既有分類
                    target_cluster_id = existing_topic_map[topic_label]
                    print(f"  🔄 歸入既有分類: {topic_label}")
                    
                    await database["clusters"].update_one(
                        {"_id": target_cluster_id},
                        {
                            "$inc": {"question_count": len(indices)},
                            "$set": {"updated_at": datetime.utcnow()}
                        }
                    )
                else:
                    # 建立新分類 (只有在額度內 AI 才會回傳新的)
                    print(f"  ✨ 建立全新分類: {topic_label}")
                    new_cluster_id = ObjectId()
                    target_cluster_id = new_cluster_id
                    
                    new_cluster_doc = {
                        "_id": new_cluster_id,
                        "course_id": cid, 
                        "topic_label": topic_label,
                        "summary": cluster_data.get("summary", ""),
                        "keywords": [], 
                        "question_count": len(indices),
                        "avg_difficulty": 0.0, 
                        "is_locked": False, 
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    await database["clusters"].insert_one(new_cluster_doc)
                    existing_topic_map[topic_label] = new_cluster_id

                # 更新問題關聯
                target_q_ids = []
                for idx in indices:
                    if isinstance(idx, int) and 0 <= idx < len(questions):
                        target_q_ids.append(ObjectId(questions[idx]['_id']))
                
                if target_q_ids:
                    await database["questions"].update_many(
                        {"_id": {"$in": target_q_ids}},
                        {"$set": {
                            "cluster_id": str(target_cluster_id),
                            "updated_at": datetime.utcnow()
                        }}
                    )

            print(f"✅ 智能分析完成！")
            
        except Exception as e:
            print(f"❌ 聚類分析失敗: {str(e)}")
            import traceback
            traceback.print_exc()

    background_tasks.add_task(_run_clustering_task, course_id, max_clusters)

    return {
        "success": True,
        "message": f"聚類分析任務已啟動 (分類上限: {max_clusters})"
    }

@router.get("/clusters/{course_id}", response_model=dict, summary="取得課程的所有聚類")
async def get_clusters_summary(course_id: str):
    """
    取得課程的所有 AI 聚類摘要 (包含尚未有提問的空分類)
    """
    from ..database import db
    
    database = db.get_db()

    # 1. 查詢條件
    match_condition = {
        "$or": [
            {"course_id": course_id},               
            {"course_id": ObjectId(course_id)}      
        ]
    }
    
    # 🔥 關鍵修正 1：先從 clusters 表撈出所有分類的「底版」 (這樣空分類才會出現)
    all_clusters_cursor = database["clusters"].find(match_condition)
    all_clusters = await all_clusters_cursor.to_list(length=None)
    
    # 2. 依然去 questions 表做聚合，用來精準計算「各分類有幾題」跟「難度」
    q_match = match_condition.copy()
    q_match["cluster_id"] = {"$ne": None}
    
    pipeline = [
        {"$match": q_match},
        {"$group": {
            "_id": "$cluster_id",
            "count": {"$sum": 1},
            "avg_difficulty": {"$avg": "$difficulty_score"},
            "keywords": {"$push": "$keywords"} 
        }}
    ]
    q_stats = await database["questions"].aggregate(pipeline).to_list(length=None)
    
    # 將聚合結果轉成字典方便查表: { "cluster_id_字串": 統計資料 }
    stats_map = {str(stat["_id"]): stat for stat in q_stats}

    # 3. 把資料組合起來回傳給前端
    response_data = []
    for cluster in all_clusters:
        c_id_str = str(cluster["_id"])
        stat = stats_map.get(c_id_str)
        
        if stat:
            # 如果這個分類有提問，就動態計算 Top 5 關鍵字
            all_keywords = []
            for kw_list in stat.get("keywords", []):
                if isinstance(kw_list, list):
                    all_keywords.extend(kw_list)
            
            keyword_freq = {}
            for kw in all_keywords:
                if kw: keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
            
            top_keywords = [kw[0] for kw in sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:5]]
            
            response_data.append({
                "cluster_id": c_id_str,
                "topic_label": cluster.get("topic_label", "未命名主題"),
                "question_count": stat["count"],
                "avg_difficulty": stat.get("avg_difficulty") or 0.0,
                "top_keywords": top_keywords
            })
        else:
            # 🔥 關鍵修正 2：如果這個分類目前「沒有提問」(例如手動剛新增的空分類)
            response_data.append({
                "cluster_id": c_id_str,
                "topic_label": cluster.get("topic_label", "未命名主題"),
                "question_count": 0,
                "avg_difficulty": 0.0,
                "top_keywords": cluster.get("keywords", [])
            })
            
    return {
        "success": True,
        "data": response_data,
        "total_clusters": len(response_data)
    }
# 示意：新增更新 Cluster 的 API
@router.patch("/clusters/{cluster_id}")
async def update_cluster(cluster_id: str, update_data: ClusterUpdate):
    """
    [新增] 手動更新聚類標籤 (助教介入)
    """
    from ..database import db
    from bson import ObjectId
    from datetime import datetime
    
    database = db.get_db()
    
    # 1. 準備更新欄位
    update_fields = {
        "updated_at": datetime.utcnow()
    }
    
    # 如果有傳入新的標題，就更新 topic_label
    if update_data.topic_label:
        update_fields["topic_label"] = update_data.topic_label
        # 同時記錄這是人工設定的標籤
        update_fields["manual_label"] = update_data.topic_label

    # 如果有指定鎖定狀態 (預設為 True)
    if update_data.is_locked is not None:
        update_fields["is_locked"] = update_data.is_locked
        
    # 2. 執行更新
    result = await database["clusters"].update_one(
        {"_id": ObjectId(cluster_id)},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        return {"success": False, "message": "找不到該聚類主題"}
        
    return {"success": True, "message": "更新成功"}


# 🔥 新增：人工手動建立聚類的模型與 API
class ManualClusterCreate(BaseModel):
    course_id: str
    topic_label: str

@router.post("/clusters/manual", summary="人工手動新增聚類主題")
async def create_manual_cluster(request: ManualClusterCreate):
    """
    允許教師/助教手動建立全新的分類，將自動視為鎖定狀態
    """
    from ..database import db
    from bson import ObjectId
    from datetime import datetime
    
    database = db.get_db()
    
    # 檢查是否已有同名標籤
    existing = await database["clusters"].find_one({
        "course_id": request.course_id, 
        "topic_label": request.topic_label
    })
    
    if existing:
        return {"success": False, "message": "該主題標籤已存在"}

    new_cluster = {
        "_id": ObjectId(),
        "course_id": request.course_id,
        "topic_label": request.topic_label,
        "summary": "人工手動建立的主題",
        "keywords": [],
        "question_count": 0,
        "avg_difficulty": 0.0,
        "is_locked": True,          # 🔥 人工建立的預設鎖定，AI 不能亂改
        "manual_label": request.topic_label,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await database["clusters"].insert_one(new_cluster)
    return {"success": True, "message": "建立成功"}

@router.delete("/clusters/{cluster_id}", summary="刪除聚類主題")
async def delete_cluster(cluster_id: str):
    """
    [新增] 刪除分類。
    刪除後，原屬於此分類的提問將恢復為「未分類」狀態。
    """
    from ..database import db
    from bson import ObjectId
    
    database = db.get_db()
    
    try:
        oid = ObjectId(cluster_id)
    except:
        return {"success": False, "message": "無效的分類 ID"}

    # 1. 把這個分類裡面的問題「釋放」出來 (把 cluster_id 設回 None)
    await database["questions"].update_many(
        {"cluster_id": cluster_id},  # 尋找屬於這個分類的問題
        {"$set": {"cluster_id": None}} # 將它們設為未分類
    )
    
    # 2. 刪除這個分類本身
    result = await database["clusters"].delete_one({"_id": oid})
    
    if result.deleted_count == 0:
        return {"success": False, "message": "找不到該分類"}
        
    return {"success": True, "message": "分類已刪除，內部提問已恢復未分類狀態"}