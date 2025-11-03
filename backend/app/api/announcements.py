"""
公告管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..models.schemas import AnnouncementCreate
from ..services.qa_service import announcement_service


router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.post("/", response_model=dict, summary="建立新公告")
async def create_announcement(
    announcement_data: AnnouncementCreate,
    created_by: str = Query("system", description="建立者ID (教師/助教)")
):
    """
    建立新公告
    
    **教師/助教端操作**
    """
    try:
        announcement = await announcement_service.create_announcement(
            announcement_data, created_by
        )
        return {
            "success": True,
            "message": "公告建立成功",
            "data": announcement
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立公告失敗: {str(e)}")


@router.get("/{announcement_id}", response_model=dict, summary="取得公告詳情")
async def get_announcement(announcement_id: str):
    """取得單一公告的詳細資訊"""
    announcement = await announcement_service.get_announcement(announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="找不到此公告")
    
    return {
        "success": True,
        "data": announcement
    }


@router.get("/", response_model=dict, summary="取得公告列表")
async def get_announcements(
    course_id: Optional[str] = Query(None, description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    is_published: Optional[bool] = Query(None, description="是否已發布"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """取得公告列表，支援篩選"""
    announcements = await announcement_service.get_announcements_by_course(
        course_id=course_id,
        class_id=class_id,
        is_published=is_published,
        skip=skip,
        limit=limit
    )
    
    return {
        "success": True,
        "data": announcements,
        "total": len(announcements)
    }


@router.patch("/{announcement_id}", response_model=dict, summary="更新公告")
async def update_announcement(announcement_id: str, update_data: dict):
    """更新公告內容"""
    announcement = await announcement_service.update_announcement(
        announcement_id, update_data
    )
    
    if not announcement:
        raise HTTPException(status_code=404, detail="找不到此公告")
    
    return {
        "success": True,
        "message": "公告更新成功",
        "data": announcement
    }


@router.post("/{announcement_id}/send-to-line", response_model=dict, summary="發送公告至 Line")
async def send_announcement_to_line(
    announcement_id: str,
    line_message_id: str = Query(..., description="Line 訊息ID")
):
    """
    標記公告已發送至 Line
    
    **由 Line Bot 服務調用**
    """
    announcement = await announcement_service.mark_sent_to_line(
        announcement_id, line_message_id
    )
    
    if not announcement:
        raise HTTPException(status_code=404, detail="找不到此公告")
    
    return {
        "success": True,
        "message": "公告已標記為發送至 Line",
        "data": announcement
    }


@router.delete("/{announcement_id}", response_model=dict, summary="刪除公告")
async def delete_announcement(announcement_id: str):
    """刪除公告 (硬刪除)"""
    success = await announcement_service.delete_announcement(announcement_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="找不到此公告")
    
    return {
        "success": True,
        "message": "公告已刪除"
    }

