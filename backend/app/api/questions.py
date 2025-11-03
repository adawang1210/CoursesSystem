"""
提問管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models.schemas import (
    Question, QuestionCreate, QuestionStatus, QuestionStatusUpdate,
    AIAnalysisResult
)
from ..services.question_service import question_service


router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/", response_model=dict, summary="建立新提問 (Line Bot 調用)")
async def create_question(question_data: QuestionCreate):
    """
    建立新提問
    
    **重要**: 此 API 會自動進行去識別化處理，line_user_id 不會被儲存
    """
    try:
        question = await question_service.create_question(question_data)
        return {
            "success": True,
            "message": "提問建立成功",
            "data": question
        }
    except ValueError as e:
        # 驗證錯誤（如課程不存在或已停用）
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立提問失敗: {str(e)}")


@router.get("/{question_id}", response_model=dict, summary="取得提問詳情")
async def get_question(question_id: str):
    """取得單一提問的詳細資訊"""
    question = await question_service.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="找不到此提問")
    
    return {
        "success": True,
        "data": question
    }


@router.get("/", response_model=dict, summary="取得提問列表")
async def get_questions(
    course_id: Optional[str] = Query(None, description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    status: Optional[QuestionStatus] = Query(None, description="提問狀態"),
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(100, ge=1, le=500, description="限制筆數")
):
    """取得提問列表，支援篩選"""
    questions = await question_service.get_questions_by_course(
        course_id=course_id,
        class_id=class_id,
        status=status,
        skip=skip,
        limit=limit
    )
    
    return {
        "success": True,
        "data": questions,
        "total": len(questions)
    }


@router.patch("/{question_id}/status", response_model=dict, summary="更新提問狀態")
async def update_question_status(
    question_id: str,
    status_update: QuestionStatusUpdate
):
    """
    更新提問狀態
    
    狀態轉換規則：
    - PENDING -> APPROVED, REJECTED, DELETED, WITHDRAWN
    - APPROVED -> DELETED
    """
    try:
        question = await question_service.update_question_status(
            question_id, status_update.status, status_update.rejection_reason
        )
        
        if not question:
            raise HTTPException(status_code=404, detail="找不到此提問或狀態轉換不合法")
        
        return {
            "success": True,
            "message": "狀態更新成功",
            "data": question
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新狀態失敗: {str(e)}")


@router.post("/{question_id}/ai-analysis", response_model=dict, summary="更新 AI 分析結果")
async def update_ai_analysis(
    question_id: str,
    analysis_result: AIAnalysisResult
):
    """
    更新提問的 AI 分析結果
    
    **此 API 由 AI/NLP 服務調用**
    """
    question = await question_service.update_ai_analysis(
        question_id, analysis_result
    )
    
    if not question:
        raise HTTPException(status_code=404, detail="找不到此提問")
    
    return {
        "success": True,
        "message": "AI 分析結果更新成功",
        "data": question
    }


@router.get("/cluster/{cluster_id}", response_model=dict, summary="取得同聚類的提問")
async def get_questions_by_cluster(
    cluster_id: str,
    course_id: str = Query(..., description="課程ID")
):
    """取得同一 AI 聚類的所有提問"""
    questions = await question_service.get_questions_by_cluster(
        course_id, cluster_id
    )
    
    return {
        "success": True,
        "data": questions,
        "total": len(questions)
    }


@router.post("/merge", response_model=dict, summary="合併提問至 Q&A")
async def merge_questions_to_qa(
    question_ids: List[str],
    qa_id: str
):
    """
    將多個提問合併至指定的 Q&A
    
    **教師/助教端操作**
    """
    count = await question_service.merge_questions_to_qa(question_ids, qa_id)
    
    return {
        "success": True,
        "message": f"成功合併 {count} 個提問",
        "merged_count": count
    }


@router.get("/statistics/", response_model=dict, summary="取得提問統計")
async def get_question_statistics(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    """取得提問統計資料"""
    stats = await question_service.get_statistics(course_id, class_id)
    
    return {
        "success": True,
        "data": stats
    }


@router.delete("/{question_id}", response_model=dict, summary="刪除提問")
async def delete_question(question_id: str):
    """刪除提問 (軟刪除)"""
    success = await question_service.delete_question(question_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="找不到此提問")
    
    return {
        "success": True,
        "message": "提問已刪除"
    }

