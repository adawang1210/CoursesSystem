"""
FastAPI 主應用程式
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database import db
from .api import questions, courses, qas, announcements, ai_integration, reports, database, line_integration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時：連線資料庫
    await db.connect_db()
    print("🚀 應用程式啟動完成")
    
    yield
    
    # 關閉時：關閉資料庫連線
    await db.close_db()
    print("👋 應用程式已關閉")


# 建立 FastAPI 應用程式
app = FastAPI(
    title="AI 教學計畫系統 API",
    description="提供課程、提問、Q&A、公告管理與 AI 整合功能",
    version="1.0.0",
    lifespan=lifespan
)


# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 註冊 API 路由
app.include_router(courses.router)
app.include_router(questions.router)
app.include_router(qas.router)
app.include_router(announcements.router)
app.include_router(ai_integration.router)
app.include_router(reports.router)
app.include_router(database.router)
app.include_router(line_integration.router)


@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "message": "歡迎使用 AI 教學計畫系統 API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "database": "connected" if db.db is not None else "disconnected",
        "ai_model": settings.GEMINI_MODEL
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )

