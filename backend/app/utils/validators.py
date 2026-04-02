"""
輸入驗證工具
"""
from bson import ObjectId
from fastapi import HTTPException


def validate_object_id(id_str: str, name: str = "ID") -> ObjectId:
    """驗證並轉換 ObjectId，無效時拋出 HTTPException"""
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail=f"無效的{name}格式: {id_str}")
    return ObjectId(id_str)
