"""
資料庫連線模組
管理 MongoDB 連線與資料庫操作
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import settings
from typing import Optional


class Database:
    """資料庫管理類別"""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect_db(cls):
        """建立資料庫連線"""
        cls.client = AsyncIOMotorClient(settings.MONGODB_URI)
        cls.db = cls.client[settings.MONGODB_DB_NAME]
        print(f"成功連線至 MongoDB: {settings.MONGODB_DB_NAME}")
    
    @classmethod
    async def close_db(cls):
        """關閉資料庫連線"""
        if cls.client:
            cls.client.close()
            print(" MongoDB 連線已關閉")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """取得資料庫實例"""
        if cls.db is None:
            raise RuntimeError("資料庫尚未連線，請先呼叫 connect_db()")
        return cls.db


# 全域資料庫實例
db = Database()

