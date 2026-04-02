"""
聚類管線整合測試
測試完整的聚類流程：取得回答 → 建構提示詞 → 呼叫 AI → 解析回應 → 寫入 DB
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from bson import ObjectId
from tests.conftest import make_question_doc, make_qa_doc


class TestGetApprovedAnswers:
    """測試取得已審核回答"""

    @pytest.mark.asyncio
    async def test_get_approved_answers(self):
        """Req 1.1, 1.3: Only approved + unclustered answers returned"""
        from app.services.question_service import QuestionService

        service = QuestionService()
        qa_id = "test_qa_id"

        approved_doc = make_question_doc(qa_id=qa_id, review_status="approved", cluster_id=None)

        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[approved_doc])
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_collection = AsyncMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.question_service.db") as patched_db:
            patched_db.get_db.return_value = mock_db
            replies = await service.get_replies_for_clustering(qa_id, limit=500)

        assert len(replies) == 1
        assert replies[0]["answer_text"] == approved_doc["question_text"]

    @pytest.mark.asyncio
    async def test_empty_answers_returns_empty_list(self):
        """Req 1.3: No approved unclustered answers returns empty list"""
        from app.services.question_service import QuestionService

        service = QuestionService()

        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_collection = AsyncMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.question_service.db") as patched_db:
            patched_db.get_db.return_value = mock_db
            replies = await service.get_replies_for_clustering("nonexistent_qa")

        assert replies == []

    @pytest.mark.asyncio
    async def test_reply_output_shape(self):
        """Req 1.2: Each reply contains _id, pseudonym, answer_text, created_at"""
        from app.services.question_service import QuestionService

        service = QuestionService()
        doc = make_question_doc(qa_id="qa1", review_status="approved", cluster_id=None, text="my answer")

        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[doc])
        mock_cursor.limit = MagicMock(return_value=mock_cursor)

        mock_collection = AsyncMock()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.services.question_service.db") as patched_db:
            patched_db.get_db.return_value = mock_db
            replies = await service.get_replies_for_clustering("qa1")

        assert len(replies) == 1
        reply = replies[0]
        assert "_id" in reply
        assert "pseudonym" in reply
        assert "answer_text" in reply
        assert "created_at" in reply


class TestFullClusteringPipeline:
    """測試完整聚類管線"""

    @pytest.mark.asyncio
    async def test_full_clustering_pipeline(self):
        """Req 4.1, 4.2, 4.3: Full pipeline creates clusters and updates questions"""
        from app.services.ai_service import AIService

        replies = [
            {"_id": str(ObjectId()), "pseudonym": "s1", "answer_text": "蝦皮是B2C", "created_at": datetime.utcnow()},
            {"_id": str(ObjectId()), "pseudonym": "s2", "answer_text": "momo是C2C", "created_at": datetime.utcnow()},
            {"_id": str(ObjectId()), "pseudonym": "s3", "answer_text": "PChome是B2C", "created_at": datetime.utcnow()},
        ]

        ai_response = {
            "clusters": [
                {"topic_label": "正確理解B2C", "summary": "學生正確理解", "question_indices": [0, 2]},
                {"topic_label": "混淆B2C與C2C", "summary": "學生混淆概念", "question_indices": [1]},
            ]
        }

        service = AIService()
        with patch.object(service, "_call_gemini", new_callable=AsyncMock) as mock_gemini:
            mock_gemini.return_value = ai_response
            result = await service.perform_qa_answer_clustering(
                student_answers=[r["answer_text"] for r in replies],
                teacher_question="請舉例兩種知名的電子商務平台",
                core_concept="了解B2C與C2C電商模式的差異",
            )

        assert "clusters" in result
        assert len(result["clusters"]) == 2
        assert result["clusters"][0]["topic_label"] == "正確理解B2C"
        assert result["clusters"][1]["question_indices"] == [1]

    @pytest.mark.asyncio
    async def test_empty_answers_returns_success(self):
        """Req 2.4, 5.1: Empty answers returns success without calling Gemini"""
        from app.services.ai_service import AIService

        service = AIService()
        result = await service.perform_qa_answer_clustering(
            student_answers=[],
            teacher_question="test",
            core_concept="test",
        )
        assert result == {"clusters": []}

    @pytest.mark.asyncio
    async def test_gemini_error_returns_empty_clusters(self):
        """Req 5.2, 5.3: When all AI services fail, perform_qa_answer_clustering raises RuntimeError"""
        from app.services.ai_service import AIService

        service = AIService()
        with patch.object(service, "_call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.side_effect = RuntimeError("All AI services unavailable")
            with pytest.raises(RuntimeError):
                await service.perform_qa_answer_clustering(
                    student_answers=["answer1"],
                    teacher_question="test",
                    core_concept="test",
                )

    @pytest.mark.asyncio
    async def test_missing_clusters_key_in_api_endpoint(self):
        """Req 4.4: When Gemini returns response without 'clusters' key, endpoint raises ValueError"""
        from app.api.ai_integration import generate_course_clusters
        from app.models.schemas import ClusterGenerateRequest

        request = ClusterGenerateRequest(
            course_id=str(ObjectId()),
            qa_id=str(ObjectId()),
            max_clusters=5,
        )

        mock_qa_doc = make_qa_doc()
        mock_qa_doc["_id"] = str(mock_qa_doc["_id"])

        mock_replies = [
            {"_id": str(ObjectId()), "pseudonym": "s1", "answer_text": "test", "created_at": datetime.utcnow()}
        ]

        # Mock the database module that is imported inside the function
        mock_database = MagicMock()
        mock_clusters_coll = AsyncMock()
        mock_clusters_coll.find = MagicMock(return_value=AsyncMock(to_list=AsyncMock(return_value=[])))
        mock_database.__getitem__ = MagicMock(return_value=mock_clusters_coll)

        with patch("app.api.ai_integration.qa_service") as mock_qa_svc, \
             patch("app.api.ai_integration.question_service") as mock_q_svc, \
             patch("app.api.ai_integration.ai_service") as mock_ai_svc, \
             patch("app.database.db") as mock_db_inst:
            mock_qa_svc.get_qa = AsyncMock(return_value=mock_qa_doc)
            mock_q_svc.get_replies_for_clustering = AsyncMock(return_value=mock_replies)
            mock_q_svc.reset_clusters_for_qa = AsyncMock()
            mock_ai_svc.perform_qa_answer_clustering = AsyncMock(return_value={"no_clusters": []})
            mock_db_inst.get_db.return_value = mock_database

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await generate_course_clusters(request)
            assert exc_info.value.status_code == 500
            assert "AI 回傳格式錯誤" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_gemini_exception_returns_500(self):
        """Req 5.3: When Gemini raises exception, endpoint returns HTTP 500"""
        from app.api.ai_integration import generate_course_clusters
        from app.models.schemas import ClusterGenerateRequest

        request = ClusterGenerateRequest(
            course_id=str(ObjectId()),
            qa_id=str(ObjectId()),
            max_clusters=5,
        )

        mock_qa_doc = make_qa_doc()
        mock_qa_doc["_id"] = str(mock_qa_doc["_id"])

        mock_replies = [
            {"_id": str(ObjectId()), "pseudonym": "s1", "answer_text": "test", "created_at": datetime.utcnow()}
        ]

        mock_database = MagicMock()
        mock_clusters_coll = AsyncMock()
        mock_clusters_coll.find = MagicMock(return_value=AsyncMock(to_list=AsyncMock(return_value=[])))
        mock_database.__getitem__ = MagicMock(return_value=mock_clusters_coll)

        with patch("app.api.ai_integration.qa_service") as mock_qa_svc, \
             patch("app.api.ai_integration.question_service") as mock_q_svc, \
             patch("app.api.ai_integration.ai_service") as mock_ai_svc, \
             patch("app.database.db") as mock_db_inst:
            mock_qa_svc.get_qa = AsyncMock(return_value=mock_qa_doc)
            mock_q_svc.get_replies_for_clustering = AsyncMock(return_value=mock_replies)
            mock_q_svc.reset_clusters_for_qa = AsyncMock()
            mock_ai_svc.perform_qa_answer_clustering = AsyncMock(
                side_effect=RuntimeError("Gemini connection failed")
            )
            mock_db_inst.get_db.return_value = mock_database

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await generate_course_clusters(request)
            assert exc_info.value.status_code == 500
