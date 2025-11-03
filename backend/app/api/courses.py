"""
課程與班級管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..models.schemas import CourseCreate, Course, ClassCreate, Class
from ..services.course_service import course_service, class_service


router = APIRouter(prefix="/courses", tags=["courses"])


# ==================== 課程管理 ====================

@router.post("/", response_model=dict, summary="建立新課程")
async def create_course(course_data: CourseCreate):
    """建立新課程"""
    try:
        course = await course_service.create_course(course_data)
        return {
            "success": True,
            "message": "課程建立成功",
            "data": course
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立課程失敗: {str(e)}")


@router.get("/{course_id}", response_model=dict, summary="取得課程詳情")
async def get_course(course_id: str):
    """取得單一課程的詳細資訊"""
    course = await course_service.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="找不到此課程")
    
    return {
        "success": True,
        "data": course
    }


@router.get("/", response_model=dict, summary="取得課程列表")
async def get_courses(
    semester: Optional[str] = Query(None, description="學期 (例: 113-1)"),
    is_active: Optional[bool] = Query(None, description="是否啟用"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """取得課程列表，支援篩選"""
    courses = await course_service.get_courses(
        semester=semester,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    
    return {
        "success": True,
        "data": courses,
        "total": len(courses)
    }


@router.patch("/{course_id}", response_model=dict, summary="更新課程")
async def update_course(course_id: str, update_data: dict):
    """更新課程資訊"""
    course = await course_service.update_course(course_id, update_data)
    
    if not course:
        raise HTTPException(status_code=404, detail="找不到此課程")
    
    return {
        "success": True,
        "message": "課程更新成功",
        "data": course
    }


@router.delete("/{course_id}", response_model=dict, summary="刪除課程")
async def delete_course(course_id: str):
    """刪除課程 (軟刪除)"""
    success = await course_service.delete_course(course_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="找不到此課程")
    
    return {
        "success": True,
        "message": "課程已刪除"
    }


@router.post("/sync", response_model=dict, summary="同步課程資料")
async def sync_courses(courses_data: List[dict]):
    """
    從外部系統同步課程資料
    
    **此 API 用於課程資料批次匯入與同步**
    """
    try:
        result = await course_service.sync_courses_from_external(courses_data)
        return {
            "success": True,
            "message": "課程同步完成",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"課程同步失敗: {str(e)}")


# ==================== 班級管理 ====================

@router.post("/{course_id}/classes", response_model=dict, summary="建立新班級")
async def create_class(course_id: str, class_data: ClassCreate):
    """在指定課程下建立新班級"""
    try:
        # 確認課程是否存在
        course = await course_service.get_course(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="找不到此課程")
        
        # 確保 class_data 的 course_id 正確
        class_data.course_id = course_id
        
        class_doc = await class_service.create_class(class_data)
        return {
            "success": True,
            "message": "班級建立成功",
            "data": class_doc
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立班級失敗: {str(e)}")


@router.get("/{course_id}/classes", response_model=dict, summary="取得課程的所有班級")
async def get_classes_by_course(
    course_id: str,
    is_active: Optional[bool] = Query(None, description="是否啟用")
):
    """取得指定課程的所有班級"""
    classes = await class_service.get_classes_by_course(
        course_id, is_active
    )
    
    return {
        "success": True,
        "data": classes,
        "total": len(classes)
    }


@router.get("/{course_id}/classes/{class_id}", response_model=dict, summary="取得班級詳情")
async def get_class(course_id: str, class_id: str):
    """取得單一班級的詳細資訊"""
    class_doc = await class_service.get_class(class_id)
    
    if not class_doc:
        raise HTTPException(status_code=404, detail="找不到此班級")
    
    if class_doc["course_id"] != course_id:
        raise HTTPException(status_code=400, detail="班級不屬於此課程")
    
    return {
        "success": True,
        "data": class_doc
    }


@router.patch("/{course_id}/classes/{class_id}", response_model=dict, summary="更新班級")
async def update_class(course_id: str, class_id: str, update_data: dict):
    """更新班級資訊"""
    class_doc = await class_service.update_class(class_id, update_data)
    
    if not class_doc:
        raise HTTPException(status_code=404, detail="找不到此班級")
    
    return {
        "success": True,
        "message": "班級更新成功",
        "data": class_doc
    }


@router.delete("/{course_id}/classes/{class_id}", response_model=dict, summary="刪除班級")
async def delete_class(course_id: str, class_id: str):
    """刪除班級 (軟刪除)"""
    success = await class_service.delete_class(class_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="找不到此班級")
    
    return {
        "success": True,
        "message": "班級已刪除"
    }

