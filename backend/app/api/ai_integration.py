"""
AI 層整合 API
提供 AI/NLP 服務調用的專用接口
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel
from ..models.schemas import (
    AIAnalysisRequest, 
    AIAnalysisResult, 
    ClusterGenerateRequest,
    ClusterUpdate
)
from ..services.question_service import question_service
from ..services.ai_service import ai_service
from ..services.qa_service import qa_service  # 🔥 新增引入 qa_service


router = APIRouter(prefix="/ai", tags=["ai-integration"])


@router.get("/questions/pending", response_model=dict, summary="取得待 AI 分析的提問")
async def get_pending_questions_for_ai(
    course_id: str = Query(..., description="課程ID"),
    limit: int = Query(100, ge=1, le=500, description="限制筆數")
):
    """取得待 AI 分析的提問列表"""
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
                errors.append({"question_id": result.question_id, "error": "找不到此提問"})
        except Exception as e:
            failed_count += 1
            errors.append({"question_id": result.question_id, "error": str(e)})
    
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
    question = await question_service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="找不到此提問")

    async def _generate_and_save_draft(qid: str, text: str):
        try:
            draft = ai_service.generate_response_draft(text)
            analysis = ai_service.analyze_question(text)
            summary = analysis.get("summary", "")

            new_difficulty = analysis.get("difficulty_score")
            if new_difficulty is None:
                old_diff = question.get("difficulty_score")
                new_difficulty = old_diff if old_diff is not None else 0.5

            new_keywords = analysis.get("keywords")
            if new_keywords is None:
                 new_keywords = question.get("keywords") or []
            
            result = AIAnalysisResult(
                question_id=qid,
                difficulty_score=float(new_difficulty),
                keywords=new_keywords,
                cluster_id=question.get("cluster_id"),
                response_draft=draft,
                summary=summary
            )
            
            await question_service.update_ai_analysis(qid, result)
        except Exception as e:
            import traceback
            traceback.print_exc()

    background_tasks.add_task(
        _generate_and_save_draft, 
        question_id, 
        question["question_text"]
    )

    return {
        "success": True,
        "message": "已開始生成草稿，請稍後重新整理頁面查看"
    }


# =========== 🔥 核心升級：雙引擎 AI 聚類 API ===========
@router.post("/clusters/generate", summary="執行課程主題或 Q&A 回答的聚類分析")
async def generate_course_clusters(
    request: ClusterGenerateRequest,
    background_tasks: BackgroundTasks
):
    course_id = request.course_id
    qa_id = request.qa_id
    max_clusters = request.max_clusters

    async def _run_clustering_task(cid: str, max_c: int, target_qa_id: Optional[str]):
        from ..database import db
        from bson import ObjectId
        from datetime import datetime
        
        try:
            database = db.get_db()

            # --- 模式 A：Q&A 批閱模式 ---
            if target_qa_id:
                print(f"🤖 [Q&A 批閱模式] 開始分析題目 {target_qa_id} 的回答...")
                
                # 1. 取得老師的題目與標準答案
                qa_doc = await qa_service.get_qa(target_qa_id)
                if not qa_doc:
                    print("❌ 找不到該 Q&A")
                    return
                
                teacher_question = qa_doc.get("question", "")
                standard_answer = qa_doc.get("answer", "")
                
                # 2. 取得學生還沒被分類的作答
                replies = await question_service.get_replies_for_clustering(target_qa_id, limit=500)
                if not replies:
                    print("✅ 沒有新的未分類回答，工作結束")
                    return
                
                q_texts = [r['answer_text'] for r in replies]
                
                # 3. 呼叫新的 AI 批閱大腦
                ai_result = ai_service.perform_qa_answer_clustering(
                    student_answers=q_texts,
                    teacher_question=teacher_question,
                    standard_answer=standard_answer,
                    max_clusters=max_c
                )
                
                if not ai_result or "clusters" not in ai_result:
                    print("❌ AI 回傳格式錯誤")
                    return
                    
                clusters_data = ai_result.get("clusters", [])
                print(f"📊 AI 將 {len(q_texts)} 個作答分成了 {len(clusters_data)} 組批閱群組")

                # 4. 寫入資料庫
                for cluster_data in clusters_data:
                    topic_label = cluster_data.get("topic_label", "未命名群組")
                    indices = cluster_data.get("question_indices", [])
                    if not indices:
                        continue
                    
                    new_cluster_id = ObjectId()
                    new_cluster_doc = {
                        "_id": new_cluster_id,
                        "course_id": cid,
                        "qa_id": target_qa_id, # 🔥 綁定 Q&A ID
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
                    
                    # 更新學生作答的 cluster_id
                    target_q_ids = []
                    for idx in indices:
                        if isinstance(idx, int) and 0 <= idx < len(replies):
                            target_q_ids.append(ObjectId(replies[idx]['_id']))
                    
                    if target_q_ids:
                        await database["questions"].update_many(
                            {"_id": {"$in": target_q_ids}},
                            {"$set": {"cluster_id": str(new_cluster_id), "updated_at": datetime.utcnow()}}
                        )
                
                print("✅ Q&A 批閱分析完成！")

            # --- 模式 B：一般提問歸納模式 (舊有邏輯保留) ---
            else:
                print(f"🤖 [一般提問模式] 開始分析課程 {cid} 的問題...")
                existing_clusters_cursor = database["clusters"].find({"course_id": cid, "qa_id": None})
                existing_clusters = await existing_clusters_cursor.to_list(length=None)
                
                existing_topic_map = {c["topic_label"]: c["_id"] for c in existing_clusters}
                existing_topic_names = list(existing_topic_map.keys())
                
                current_count = len(existing_topic_names)
                remaining_quota = max(0, max_c - current_count)
                
                questions = await question_service.get_pending_questions_for_ai(cid, limit=50)
                if not questions:
                    return

                q_texts = [q['question_text'] for q in questions]
                ai_result = ai_service.perform_advanced_clustering(
                    q_texts, max_new_topics=remaining_quota, existing_topics=existing_topic_names
                )
                
                if not ai_result or "clusters" not in ai_result: return
                clusters_data = ai_result.get("clusters", [])

                for cluster_data in clusters_data:
                    topic_label = cluster_data.get("topic_label", "未命名群組")
                    indices = cluster_data.get("question_indices", [])
                    if not indices: continue
                    
                    if topic_label in existing_topic_map:
                        target_cluster_id = existing_topic_map[topic_label]
                        await database["clusters"].update_one(
                            {"_id": target_cluster_id},
                            {"$inc": {"question_count": len(indices)}, "$set": {"updated_at": datetime.utcnow()}}
                        )
                    else:
                        new_cluster_id = ObjectId()
                        target_cluster_id = new_cluster_id
                        new_cluster_doc = {
                            "_id": new_cluster_id, "course_id": cid, "qa_id": None,
                            "topic_label": topic_label, "summary": cluster_data.get("summary", ""),
                            "keywords": [], "question_count": len(indices), "avg_difficulty": 0.0, 
                            "is_locked": False, "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()
                        }
                        await database["clusters"].insert_one(new_cluster_doc)
                        existing_topic_map[topic_label] = new_cluster_id

                    target_q_ids = []
                    for idx in indices:
                        if isinstance(idx, int) and 0 <= idx < len(questions):
                            target_q_ids.append(ObjectId(questions[idx]['_id']))
                    if target_q_ids:
                        await database["questions"].update_many(
                            {"_id": {"$in": target_q_ids}},
                            {"$set": {"cluster_id": str(target_cluster_id), "updated_at": datetime.utcnow()}}
                        )
                print("✅ 一般提問分析完成！")

        except Exception as e:
            print(f"❌ 聚類分析失敗: {str(e)}")
            import traceback
            traceback.print_exc()

    # 啟動背景任務
    background_tasks.add_task(_run_clustering_task, course_id, max_clusters, qa_id)

    return {
        "success": True,
        "message": f"聚類分析任務已啟動 ({'Q&A 批閱模式' if qa_id else '一般提問模式'})"
    }
# =========================================================


@router.get("/clusters/{course_id}", response_model=dict, summary="取得課程的所有聚類")
async def get_clusters_summary(
    course_id: str,
    qa_id: Optional[str] = Query(None, description="指定 Q&A 的 ID (選填)") # 🔥 支援 QA ID 篩選
):
    """
    取得課程的 AI 聚類摘要
    如果不傳 qa_id，預設只回傳「一般提問」的分類。如果傳了，就只回傳針對該題的批閱分類。
    """
    from ..database import db
    database = db.get_db()

    # 1. 設定 clusters 的查詢條件
    cluster_match = {"course_id": course_id}
    if qa_id:
        cluster_match["qa_id"] = qa_id
    else:
        cluster_match["qa_id"] = None # 預設只抓一般問題的分類

    all_clusters_cursor = database["clusters"].find(cluster_match)
    all_clusters = await all_clusters_cursor.to_list(length=None)
    
    # 2. 設定 questions 表的聚合條件 (用於計算每個分類確實有幾題)
    q_match = {"course_id": course_id, "cluster_id": {"$ne": None}}
    if qa_id:
        q_match["reply_to_qa_id"] = qa_id
    else:
        q_match["reply_to_qa_id"] = None
        
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
    stats_map = {str(stat["_id"]): stat for stat in q_stats}

    # 3. 組合資料
    response_data = []
    for cluster in all_clusters:
        c_id_str = str(cluster["_id"])
        stat = stats_map.get(c_id_str)
        
        if stat:
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
                "summary": cluster.get("summary", ""), # 🔥 加回傳 summary，讓前端能顯示批閱結果
                "question_count": stat["count"],
                "avg_difficulty": stat.get("avg_difficulty") or 0.0,
                "top_keywords": top_keywords
            })
        else:
            response_data.append({
                "cluster_id": c_id_str,
                "topic_label": cluster.get("topic_label", "未命名主題"),
                "summary": cluster.get("summary", ""),
                "question_count": 0,
                "avg_difficulty": 0.0,
                "top_keywords": cluster.get("keywords", [])
            })
            
    return {
        "success": True,
        "data": response_data,
        "total_clusters": len(response_data)
    }


@router.patch("/clusters/{cluster_id}")
async def update_cluster(cluster_id: str, update_data: ClusterUpdate):
    from ..database import db
    from bson import ObjectId
    from datetime import datetime
    
    database = db.get_db()
    update_fields = {"updated_at": datetime.utcnow()}
    
    if update_data.topic_label:
        update_fields["topic_label"] = update_data.topic_label
        update_fields["manual_label"] = update_data.topic_label

    if update_data.is_locked is not None:
        update_fields["is_locked"] = update_data.is_locked
        
    result = await database["clusters"].update_one(
        {"_id": ObjectId(cluster_id)},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        return {"success": False, "message": "找不到該聚類主題"}
        
    return {"success": True, "message": "更新成功"}


class ManualClusterCreate(BaseModel):
    course_id: str
    topic_label: str
    qa_id: Optional[str] = None  # 🔥 支援手動建立特定 Q&A 的分類

@router.post("/clusters/manual", summary="人工手動新增聚類主題")
async def create_manual_cluster(request: ManualClusterCreate):
    from ..database import db
    from bson import ObjectId
    from datetime import datetime
    
    database = db.get_db()
    
    existing = await database["clusters"].find_one({
        "course_id": request.course_id, 
        "qa_id": request.qa_id,
        "topic_label": request.topic_label
    })
    
    if existing:
        return {"success": False, "message": "該主題標籤已存在"}

    new_cluster = {
        "_id": ObjectId(),
        "course_id": request.course_id,
        "qa_id": request.qa_id,
        "topic_label": request.topic_label,
        "summary": "人工手動建立的主題",
        "keywords": [],
        "question_count": 0,
        "avg_difficulty": 0.0,
        "is_locked": True, 
        "manual_label": request.topic_label,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await database["clusters"].insert_one(new_cluster)
    return {"success": True, "message": "建立成功"}


@router.delete("/clusters/{cluster_id}", summary="刪除聚類主題")
async def delete_cluster(cluster_id: str):
    from ..database import db
    from bson import ObjectId
    
    database = db.get_db()
    
    try:
        oid = ObjectId(cluster_id)
    except:
        return {"success": False, "message": "無效的分類 ID"}

    await database["questions"].update_many(
        {"cluster_id": cluster_id},  
        {"$set": {"cluster_id": None}} 
    )
    
    result = await database["clusters"].delete_one({"_id": oid})
    
    if result.deleted_count == 0:
        return {"success": False, "message": "找不到該分類"}
        
    return {"success": True, "message": "分類已刪除，內部提問已恢復未分類狀態"}