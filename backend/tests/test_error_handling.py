"""
錯誤處理測試
測試 ObjectId 驗證、CORS 設定等
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestInvalidObjectId:
    """Req 8.2, 10.1: Invalid ObjectId returns HTTP 400"""

    def _get_client(self):
        """Create a TestClient with mocked database"""
        with patch("app.database.db") as mock_db_module:
            mock_database = MagicMock()
            mock_db_module.get_db.return_value = mock_database
            mock_db_module.db = mock_database
            mock_db_module.connect_db = AsyncMock()
            mock_db_module.close_db = AsyncMock()
            mock_db_module.ensure_indexes = AsyncMock()

            from app.main import app
            client = TestClient(app, raise_server_exceptions=False)
            return client

    def test_invalid_object_id_question_get(self):
        """Invalid ObjectId on GET /questions/{id} returns 400"""
        client = self._get_client()
        response = client.get("/questions/invalid-id-here")
        assert response.status_code == 400

    def test_invalid_object_id_question_review(self):
        """Invalid ObjectId on PATCH /questions/{id}/review returns 400"""
        client = self._get_client()
        response = client.patch(
            "/questions/not-a-valid-oid/review",
            json={"review_status": "approved"},
        )
        assert response.status_code == 400

    def test_invalid_object_id_question_delete(self):
        """Invalid ObjectId on DELETE /questions/{id} returns 400"""
        client = self._get_client()
        response = client.delete("/questions/bad_id")
        assert response.status_code == 400

    def test_invalid_object_id_cluster_get(self):
        """Invalid ObjectId on GET /ai/clusters/{course_id} returns 400"""
        client = self._get_client()
        # The endpoint calls db.get_db() before validate_object_id,
        # so we need to mock the database to let it reach validation
        with patch("app.database.db") as mock_db_inst:
            mock_database = MagicMock()
            mock_db_inst.get_db.return_value = mock_database
            mock_db_inst.db = mock_database
            response = client.get("/ai/clusters/not-valid")
        assert response.status_code == 400


class TestCORSConfiguration:
    """Req 10.2, 10.3: CORS uses explicit methods and headers"""

    def test_cors_uses_explicit_methods(self):
        """Check app middleware configuration for explicit methods list"""
        from app.main import app

        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware):
                cors_middleware = middleware
                break

        assert cors_middleware is not None, "CORSMiddleware not found"
        methods = cors_middleware.kwargs.get("allow_methods", [])
        # Should NOT be wildcard
        assert "*" not in methods, "CORS allow_methods should not use wildcard"
        # Should contain explicit methods
        assert "GET" in methods
        assert "POST" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods
        assert "OPTIONS" in methods

    def test_cors_uses_explicit_headers(self):
        """Check app middleware configuration for explicit headers list"""
        from app.main import app

        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware):
                cors_middleware = middleware
                break

        assert cors_middleware is not None, "CORSMiddleware not found"
        headers = cors_middleware.kwargs.get("allow_headers", [])
        # Should NOT be wildcard
        assert "*" not in headers, "CORS allow_headers should not use wildcard"
        # Should contain explicit headers
        assert "Content-Type" in headers
        assert "Authorization" in headers
