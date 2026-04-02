"""
日期時間處理工具
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> datetime:
    """取得當前 UTC 時間"""
    return datetime.now(timezone.utc)


def to_taiwan_time(dt: datetime) -> datetime:
    """轉換為台灣時間 (UTC+8)"""
    from datetime import timedelta
    return dt + timedelta(hours=8)


def format_datetime(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期時間"""
    if dt is None:
        return ""
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """解析日期時間字串"""
    try:
        return datetime.strptime(date_str, format_str)
    except ValueError:
        return None



def build_date_range_query(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    field_name: str = "created_at"
) -> Dict[str, Any]:
    """建構 MongoDB 日期區間查詢條件"""
    if not start_date and not end_date:
        return {}
    date_filter = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        adjusted_end = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        date_filter["$lte"] = adjusted_end
    if date_filter:
        return {field_name: date_filter}
    return {}
