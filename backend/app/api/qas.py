"""
Q&A 管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from ..models.schemas import QACreate
from ..services.qa_service import qa_service


router = APIRouter(prefix="/qas", tags=["qas"])


@router.post("/", response_model=dict, summary="建立新 Q&A")
async def create_qa(
    qa_data: QACreate,
    created_by: str = Query(..., description="建立者ID (教師/助教)")
):
    """
    建立新 Q&A (支援限時推播)
    
    **教師/助教端操作**
    """
    try:
        qa = await qa_service.create_qa(qa_data, created_by)
        return {
            "success": True,
            "message": "Q&A 建立成功",
            "data": qa
        }
    except ValueError as e:
        # 課程不存在等驗證錯誤
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立 Q&A 失敗: {str(e)}")


@router.get("/{qa_id}", response_model=dict, summary="取得 Q&A 詳情")
async def get_qa(qa_id: str):
    """取得單一 Q&A 的詳細資訊"""
    qa = await qa_service.get_qa(qa_id)
    if not qa:
        raise HTTPException(status_code=404, detail="找不到此 Q&A")
    
    return {
        "success": True,
        "data": qa
    }


# =========== 🔥 新增：取得特定 Q&A 的所有學生回覆 ===========
@router.get("/{qa_id}/replies", response_model=dict, summary="取得對此 Q&A 的學生回覆")
async def get_qa_replies(qa_id: str):
    """
    取得特定 Q&A 的所有學生回覆紀錄
    這會提供給前端的對話泡泡面板使用
    """
    replies = await qa_service.get_qa_replies(qa_id)
    
    return {
        "success": True,
        "data": replies,
        "total": len(replies)
    }
# =========================================================


@router.get("/", response_model=dict, summary="取得 Q&A 列表")
async def get_qas(
    course_id: Optional[str] = Query(None, description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    is_published: Optional[bool] = Query(None, description="是否已發布"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """取得 Q&A 列表，支援篩選"""
    qas = await qa_service.get_qas_by_course(
        course_id=course_id,
        class_id=class_id,
        is_published=is_published,
        skip=skip,
        limit=limit
    )
    
    return {
        "success": True,
        "data": qas,
        "total": len(qas)
    }


@router.patch("/{qa_id}", response_model=dict, summary="更新 Q&A")
async def update_qa(qa_id: str, update_data: dict):
    """更新 Q&A 內容"""
    qa = await qa_service.update_qa(qa_id, update_data)
    
    if not qa:
        raise HTTPException(status_code=404, detail="找不到此 Q&A")
    
    return {
        "success": True,
        "message": "Q&A 更新成功",
        "data": qa
    }


@router.post("/{qa_id}/stop", response_model=dict, summary="提前結束限時 Q&A")
async def stop_qa_replies(qa_id: str):
    """
    將 Q&A 的截止時間設為現在，立即停止接收學生的回覆
    """
    qa = await qa_service.update_qa(qa_id, {"expires_at": datetime.utcnow()})
    
    if not qa:
        raise HTTPException(status_code=404, detail="找不到此 Q&A")
    
    return {
        "success": True,
        "message": "已提前結束限時回覆",
        "data": qa
    }


@router.post("/{qa_id}/link-questions", response_model=dict, summary="連結提問至 Q&A")
async def link_questions_to_qa(
    qa_id: str,
    question_ids: List[str]
):
    """
    將提問連結至此 Q&A
    
    **教師/助教端操作**：將聚類的提問合併至 Q&A
    """
    qa = await qa_service.link_questions_to_qa(qa_id, question_ids)
    
    if not qa:
        raise HTTPException(status_code=404, detail="找不到此 Q&A")
    
    return {
        "success": True,
        "message": f"成功連結 {len(question_ids)} 個提問",
        "data": qa
    }


@router.delete("/{qa_id}", response_model=dict, summary="刪除 Q&A")
async def delete_qa(qa_id: str):
    """刪除 Q&A (硬刪除)"""
    success = await qa_service.delete_qa(qa_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="找不到此 Q&A")
    
    return {
        "success": True,
        "message": "Q&A 已刪除"
    }


@router.get("/search/", response_model=dict, summary="搜尋 Q&A")
async def search_qas(
    course_id: str = Query(..., description="課程ID"),
    keyword: str = Query(..., description="搜尋關鍵字"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """搜尋 Q&A 內容"""
    qas = await qa_service.search_qas(course_id, keyword, skip, limit)
    
    return {
        "success": True,
        "data": qas,
        "total": len(qas)
    }