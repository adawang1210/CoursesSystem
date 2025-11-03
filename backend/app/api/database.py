"""
資料庫管理 API 路由
提供資料庫統計、集合查看等管理功能
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from ..database import db
from datetime import datetime
from bson import ObjectId


router = APIRouter(prefix="/database", tags=["database"])


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """序列化 MongoDB 文件，將 ObjectId 轉換為字串"""
    if doc is None:
        return None
    
    serialized = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, dict):
            serialized[key] = serialize_doc(value)
        elif isinstance(value, list):
            serialized[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
        else:
            serialized[key] = value
    return serialized


@router.get("/overview", summary="取得資料庫概覽")
async def get_database_overview():
    """
    取得資料庫的整體概覽資訊
    包含所有集合的統計資料
    """
    try:
        database = db.get_db()
        
        # 獲取所有集合名稱
        collection_names = await database.list_collection_names()
        
        # 統計各集合資料
        collections_stats = []
        total_documents = 0
        
        for collection_name in collection_names:
            collection = database[collection_name]
            count = await collection.count_documents({})
            total_documents += count
            
            # 獲取集合的儲存資訊
            stats = await database.command("collStats", collection_name)
            
            collections_stats.append({
                "name": collection_name,
                "count": count,
                "size": stats.get("size", 0),
                "avgObjSize": stats.get("avgObjSize", 0),
                "storageSize": stats.get("storageSize", 0),
                "indexes": stats.get("nindexes", 0)
            })
        
        return {
            "success": True,
            "data": {
                "database_name": database.name,
                "total_collections": len(collection_names),
                "total_documents": total_documents,
                "collections": collections_stats
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取資料庫概覽失敗: {str(e)}")


@router.get("/collections/{collection_name}", summary="取得集合資料")
async def get_collection_data(
    collection_name: str,
    skip: int = Query(0, ge=0, description="跳過的筆數"),
    limit: int = Query(20, ge=1, le=100, description="限制返回的筆數"),
    sort_field: Optional[str] = Query(None, description="排序欄位"),
    sort_order: int = Query(-1, description="排序順序 (1: 升序, -1: 降序)")
):
    """
    取得特定集合的資料
    支援分頁、排序
    """
    try:
        database = db.get_db()
        
        # 檢查集合是否存在
        collection_names = await database.list_collection_names()
        if collection_name not in collection_names:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")
        
        collection = database[collection_name]
        
        # 獲取總數
        total = await collection.count_documents({})
        
        # 構建排序條件
        sort_criteria = []
        if sort_field:
            sort_criteria.append((sort_field, sort_order))
        else:
            # 預設按 _id 或 created_at 排序
            sort_criteria.append(("_id", -1))
        
        # 查詢資料
        cursor = collection.find().sort(sort_criteria).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        # 序列化文件
        serialized_docs = [serialize_doc(doc) for doc in documents]
        
        return {
            "success": True,
            "data": {
                "collection": collection_name,
                "total": total,
                "skip": skip,
                "limit": limit,
                "documents": serialized_docs
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取集合資料失敗: {str(e)}")


@router.get("/collections/{collection_name}/sample", summary="取得集合樣本")
async def get_collection_sample(
    collection_name: str,
    sample_size: int = Query(5, ge=1, le=10, description="樣本大小")
):
    """
    隨機取得集合的樣本資料
    用於快速預覽集合結構
    """
    try:
        database = db.get_db()
        
        # 檢查集合是否存在
        collection_names = await database.list_collection_names()
        if collection_name not in collection_names:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")
        
        collection = database[collection_name]
        
        # 使用 aggregate 的 $sample 獲取隨機樣本
        pipeline = [{"$sample": {"size": sample_size}}]
        cursor = collection.aggregate(pipeline)
        documents = await cursor.to_list(length=sample_size)
        
        # 序列化文件
        serialized_docs = [serialize_doc(doc) for doc in documents]
        
        return {
            "success": True,
            "data": {
                "collection": collection_name,
                "sample_size": len(serialized_docs),
                "documents": serialized_docs
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取集合樣本失敗: {str(e)}")


@router.get("/collections/{collection_name}/schema", summary="分析集合結構")
async def analyze_collection_schema(collection_name: str):
    """
    分析集合的欄位結構
    返回所有欄位及其類型
    """
    try:
        database = db.get_db()
        
        # 檢查集合是否存在
        collection_names = await database.list_collection_names()
        if collection_name not in collection_names:
            raise HTTPException(status_code=404, detail=f"集合 '{collection_name}' 不存在")
        
        collection = database[collection_name]
        
        # 取得一些樣本來分析結構
        sample_docs = await collection.find().limit(10).to_list(length=10)
        
        if not sample_docs:
            return {
                "success": True,
                "data": {
                    "collection": collection_name,
                    "fields": []
                }
            }
        
        # 分析欄位
        fields_info = {}
        for doc in sample_docs:
            for key, value in doc.items():
                if key not in fields_info:
                    fields_info[key] = {
                        "name": key,
                        "types": set(),
                        "sample_values": []
                    }
                
                value_type = type(value).__name__
                fields_info[key]["types"].add(value_type)
                
                # 記錄前幾個樣本值
                if len(fields_info[key]["sample_values"]) < 3:
                    if isinstance(value, (str, int, float, bool)):
                        fields_info[key]["sample_values"].append(value)
                    elif isinstance(value, ObjectId):
                        fields_info[key]["sample_values"].append(str(value))
                    elif isinstance(value, datetime):
                        fields_info[key]["sample_values"].append(value.isoformat())
        
        # 轉換為列表格式
        fields = [
            {
                "name": info["name"],
                "types": list(info["types"]),
                "sample_values": info["sample_values"]
            }
            for info in fields_info.values()
        ]
        
        return {
            "success": True,
            "data": {
                "collection": collection_name,
                "total_documents": await collection.count_documents({}),
                "fields": fields
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析集合結構失敗: {str(e)}")

