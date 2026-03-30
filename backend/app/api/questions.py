"""
作答回覆管理 API 路由 (原提問管理)
處理學生對 Q&A 任務的作答紀錄與批閱
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional
# 🔥 修改：引入 ReviewStatusBatchUpdate
from ..models.schemas import QuestionCreate, ReviewStatusUpdate, ReviewStatusBatchUpdate
from ..services.question_service import question_service

router = APIRouter(prefix="/questions", tags=["questions"])

@router.post("/", response_model=dict, summary="建立新提問/作答 (Line Bot 調用)")
async def create_question(question_data: QuestionCreate, background_tasks: BackgroundTasks):
    """
    建立新提問或作答
    
    **重要**: 此 API 會自動進行去識別化處理，line_user_id 不會被儲存
    """
    try:
        question = await question_service.create_question(question_data, background_tasks)
        return {
            "success": True,
            "message": "作答紀錄建立成功",
            "data": question
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立作答失敗: {str(e)}")


@router.get("/{question_id}", response_model=dict, summary="取得作答詳情")
async def get_question(question_id: str):
    """取得單一作答的詳細資訊"""
    question = await question_service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="找不到此作答紀錄")
    
    return {
        "success": True,
        "data": question
    }


@router.get("/", response_model=dict, summary="取得作答列表")
async def get_questions(
    course_id: Optional[str] = Query(None, description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(100, ge=1, le=500, description="限制筆數")
):
    """取得作答列表，支援篩選"""
    questions = await question_service.get_questions_by_course(
        course_id=course_id,
        class_id=class_id,
        skip=skip,
        limit=limit
    )
    
    return {
        "success": True,
        "data": questions,
        "total": len(questions)
    }


@router.patch("/{question_id}/review", response_model=dict, summary="更新作答批閱狀態")
async def update_review_status(
    question_id: str,
    review_data: ReviewStatusUpdate
):
    """
    更新學生的作答批閱狀態與評語 (教師/助教使用)
    """
    question = await question_service.update_review_status(
        question_id=question_id,
        review_status=review_data.review_status,
        feedback=review_data.feedback
    )
    
    if not question:
        raise HTTPException(status_code=404, detail="找不到此作答紀錄")
        
    return {
        "success": True,
        "message": "批閱狀態更新成功",
        "data": question
    }


# =========== 🔥 新增：批量更新作答批閱狀態的 API ===========
@router.post("/batch-review", response_model=dict, summary="批量更新作答批閱狀態")
async def batch_update_review_status(batch_data: ReviewStatusBatchUpdate):
    """
    一次更新多個學生作答的批閱狀態 (教師/助教批量操作使用)
    """
    success_count = 0
    failed_count = 0
    
    for q_id in batch_data.question_ids:
        try:
            # 沿用原本的單筆更新服務，跑迴圈處理
            updated_question = await question_service.update_review_status(
                question_id=q_id,
                review_status=batch_data.review_status,
                feedback=batch_data.feedback
            )
            if updated_question:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1
            print(f"批量更新作答 {q_id} 失敗: {str(e)}")
            
    return {
        "success": True,
        "message": f"批量批閱完成！成功: {success_count} 筆，失敗: {failed_count} 筆",
        "success_count": success_count,
        "failed_count": failed_count
    }
# ========================================================


@router.get("/cluster/{cluster_id}", response_model=dict, summary="取得同聚類的作答")
async def get_questions_by_cluster(
    cluster_id: str,
    course_id: str = Query(..., description="課程ID")
):
    """取得同一 AI 聚類的所有作答紀錄"""
    questions = await question_service.get_questions_by_cluster(
        course_id, cluster_id
    )
    
    return {
        "success": True,
        "data": questions,
        "total": len(questions)
    }


@router.delete("/{question_id}", response_model=dict, summary="刪除作答")
async def delete_question(question_id: str):
    """刪除作答 (直接刪除)"""
    success = await question_service.delete_question(question_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="找不到此作答紀錄")
    
    return {
        "success": True,
        "message": "作答紀錄已刪除"
    }