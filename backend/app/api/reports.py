"""
報表匯出 API 路由
"""
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional
from datetime import datetime
from ..services.export_service import export_service


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export/questions", summary="匯出提問資料 CSV")
async def export_questions_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID"),
    cluster_id: Optional[str] = Query(None, description="聚類ID (篩選特定主題)"),
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)")
):
    """
    匯出提問資料為 CSV 格式
    
    **教師/助教端操作**
    
    **重要**：匯出的資料僅包含去識別化後的 pseudonym，不包含原始 Line User ID
    """
    try:
        # 解析日期
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 生成 CSV
        csv_content = await export_service.export_questions_to_csv(
            course_id=course_id,
            class_id=class_id,
            cluster_id=cluster_id,
            start_date=start_dt,
            end_date=end_dt
        )
        
        # 設定檔案名稱
        filename = f"questions_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 返回 CSV 檔案
        return Response(
            content=csv_content.encode('utf-8-sig'),  # 使用 BOM 以支援中文
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")
    
@router.get("/export/clusters", summary="匯出 AI 主題分析報表 CSV")
async def export_clusters_csv(
    course_id: str = Query(..., description="課程ID")
):
    """
    匯出課程的 AI 主題分析結果
    
    包含：
    - 主題名稱 (Topic Label)
    - 摘要 (Summary)
    - 包含的問題數
    - 平均難度
    - 代表關鍵字
    """
    try:
        # 呼叫 export_service (假設您會在 service 層實作此邏輯)
        csv_content = await export_service.export_clusters_to_csv(
            course_id=course_id
        )
        
        filename = f"clusters_analysis_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")
# ==========================================================


@router.get("/export/qas", summary="匯出 Q&A 資料 CSV")
async def export_qas_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    """
    匯出 Q&A 資料為 CSV 格式
    """
    try:
        csv_content = await export_service.export_qas_to_csv(
            course_id=course_id,
            class_id=class_id
        )
        
        filename = f"qas_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")


@router.get("/export/statistics", summary="匯出統計資料 CSV")
async def export_statistics_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    """
    匯出統計資料為 CSV 格式
    """
    try:
        csv_content = await export_service.export_statistics_to_csv(
            course_id=course_id,
            class_id=class_id
        )
        
        filename = f"statistics_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

@router.get("/export/qas", summary="匯出 Q&A 資料 CSV")
async def export_qas_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    """
    匯出 Q&A 資料為 CSV 格式
    
    **教師/助教端操作**
    """
    try:
        # 生成 CSV
        csv_content = await export_service.export_qas_to_csv(
            course_id=course_id,
            class_id=class_id
        )
        
        # 設定檔案名稱
        filename = f"qas_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 返回 CSV 檔案
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")


@router.get("/export/statistics", summary="匯出統計資料 CSV")
async def export_statistics_csv(
    course_id: str = Query(..., description="課程ID"),
    class_id: Optional[str] = Query(None, description="班級ID")
):
    """
    匯出統計資料為 CSV 格式
    
    包含：
    - 各狀態的提問數量統計
    - 各聚類的提問數量統計
    - 難度分布統計
    
    **教師/助教端操作**
    """
    try:
        # 生成 CSV
        csv_content = await export_service.export_statistics_to_csv(
            course_id=course_id,
            class_id=class_id
        )
        
        # 設定檔案名稱
        filename = f"statistics_{course_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 返回 CSV 檔案
        return Response(
            content=csv_content.encode('utf-8-sig'),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗: {str(e)}")

