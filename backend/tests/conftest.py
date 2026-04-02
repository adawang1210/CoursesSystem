"""
共用測試 fixtures
提供 mock MongoDB、mock AIService、test data factory functions
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from bson import ObjectId


@pytest.fixture
def mock_db():
    """Mock MongoDB database"""
    db = AsyncMock()
    db.__getitem__ = MagicMock(return_value=AsyncMock())
    return db


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for testing"""
    monkeypatch.setattr("app.config.settings.GEMINI_API_KEY", "test-api-key")
    monkeypatch.setattr("app.config.settings.GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setattr("app.config.settings.GEMINI_RETRY_MAX_ATTEMPTS", 3)
    monkeypatch.setattr("app.config.settings.GEMINI_RETRY_BASE_DELAY", 0.01)
    monkeypatch.setattr("app.config.settings.GEMINI_TIMEOUT_SECONDS", 5.0)


def make_question_doc(qa_id="test_qa_id", review_status="approved", cluster_id=None, text="test answer"):
    """Factory for question documents"""
    return {
        "_id": ObjectId(),
        "course_id": "test_course_id",
        "reply_to_qa_id": qa_id,
        "pseudonym": "test_pseudo",
        "student_id": "111400000",
        "question_text": text,
        "review_status": review_status,
        "cluster_id": cluster_id,
        "difficulty_score": None,
        "keywords": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


def make_qa_doc(course_id="test_course_id"):
    """Factory for QA documents"""
    return {
        "_id": ObjectId(),
        "course_id": course_id,
        "question": "請舉例兩種知名的電子商務平台",
        "core_concept": "了解B2C與C2C電商模式的差異",
        "expected_misconceptions": "學生可能混淆平台類型",
        "allow_replies": True,
        "is_published": True,
        "created_at": datetime.utcnow(),
    }
