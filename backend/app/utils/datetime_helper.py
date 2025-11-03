"""
日期時間處理工具
"""
from datetime import datetime, timezone
from typing import Optional


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

