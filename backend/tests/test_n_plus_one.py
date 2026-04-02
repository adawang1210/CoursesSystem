"""
N+1 查詢消除驗證測試
驗證重構後的方法使用批次操作而非迴圈逐筆查詢
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from datetime import datetime


class TestGetCoursesUsesAggregation:
    """Req 6.1: get_courses uses aggregation pipeline instead of per-course count_documents"""

    @pytest.mark.asyncio
    async def test_get_courses_uses_aggregation(self):
        """Verify aggregate() is called instead of count_documents() in a loop"""
        from app.services.course_service import CourseService

        service = CourseService()

        course1 = {"_id": ObjectId(), "course_name": "Course A", "semester": "113-1", "is_active": True}
        course2 = {"_id": ObjectId(), "course_name": "Course B", "semester": "113-1", "is_active": True}
        courses = [course1, course2]

        cid1 = str(course1["_id"])
        cid2 = str(course2["_id"])

        # Mock cursor for courses
        mock_courses_cursor = AsyncMock()
        mock_courses_cursor.to_list = AsyncMock(return_value=courses)
        mock_courses_cursor.skip = MagicMock(return_value=mock_courses_cursor)
        mock_courses_cursor.limit = MagicMock(return_value=mock_courses_cursor)

        # Mock questions aggregate
        q_agg_result = [{"_id": cid1, "count": 5}, {"_id": cid2, "count": 3}]
        mock_q_agg_cursor = AsyncMock()
        mock_q_agg_cursor.to_list = AsyncMock(return_value=q_agg_result)

        # Mock line_users aggregate
        s_agg_result = [{"_id": cid1, "count": 10}]
        mock_s_agg_cursor = AsyncMock()
        mock_s_agg_cursor.to_list = AsyncMock(return_value=s_agg_result)

        # Setup collections
        mock_courses_coll = AsyncMock()
        mock_courses_coll.find = MagicMock(return_value=mock_courses_cursor)

        mock_questions_coll = AsyncMock()
        mock_questions_coll.aggregate = MagicMock(return_value=mock_q_agg_cursor)

        mock_line_users_coll = AsyncMock()
        mock_line_users_coll.aggregate = MagicMock(return_value=mock_s_agg_cursor)

        def get_collection(name):
            if name == "courses":
                return mock_courses_coll
            elif name == "questions":
                return mock_questions_coll
            elif name == "line_users":
                return mock_line_users_coll
            return AsyncMock()

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch("app.services.course_service.db") as patched_db:
            patched_db.get_db.return_value = mock_db
            result = await service.get_courses()

        # Verify aggregate was called on questions and line_users (batch operation)
        mock_questions_coll.aggregate.assert_called_once()
        mock_line_users_coll.aggregate.assert_called_once()

        # Verify count_documents was NOT called (no N+1)
        mock_questions_coll.count_documents.assert_not_called()
        mock_line_users_coll.count_documents.assert_not_called()

        # Verify correct counts
        assert result[0]["question_count"] == 5
        assert result[0]["student_count"] == 10
        assert result[1]["question_count"] == 3
        assert result[1]["student_count"] == 0


class TestExportQasUsesBulkQuery:
    """Req 6.2: export_qas_to_csv uses bulk query instead of per-QA find"""

    @pytest.mark.asyncio
    async def test_export_qas_uses_bulk_query(self):
        """Verify a single find() with $in is used instead of per-QA queries"""
        from app.services.export_service import ExportService

        service = ExportService()

        qa1_id = ObjectId()
        qa2_id = ObjectId()
        qas = [
            {"_id": qa1_id, "course_id": "c1", "question": "Q1", "tags": [], "is_published": True, "created_at": datetime.utcnow()},
            {"_id": qa2_id, "course_id": "c1", "question": "Q2", "tags": [], "is_published": True, "created_at": datetime.utcnow()},
        ]

        replies = [
            {"_id": ObjectId(), "reply_to_qa_id": str(qa1_id), "pseudonym": "s1", "question_text": "ans1", "created_at": datetime.utcnow()},
            {"_id": ObjectId(), "reply_to_qa_id": str(qa2_id), "pseudonym": "s2", "question_text": "ans2", "created_at": datetime.utcnow()},
        ]

        # Mock QA cursor
        mock_qa_cursor = AsyncMock()
        mock_qa_cursor.to_list = AsyncMock(return_value=qas)
        mock_qa_cursor.sort = MagicMock(return_value=mock_qa_cursor)

        # Mock replies cursor (single bulk query)
        mock_replies_cursor = AsyncMock()
        mock_replies_cursor.to_list = AsyncMock(return_value=replies)
        mock_replies_cursor.sort = MagicMock(return_value=mock_replies_cursor)

        mock_qa_coll = AsyncMock()
        mock_qa_coll.find = MagicMock(return_value=mock_qa_cursor)

        mock_q_coll = AsyncMock()
        mock_q_coll.find = MagicMock(return_value=mock_replies_cursor)

        def get_collection(name):
            if name == "qas":
                return mock_qa_coll
            elif name == "questions":
                return mock_q_coll
            return AsyncMock()

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch("app.services.export_service.db") as patched_db:
            patched_db.get_db.return_value = mock_db
            csv_result = await service.export_qas_to_csv(course_id="c1")

        # Verify questions collection find was called exactly once (bulk query)
        assert mock_q_coll.find.call_count == 1

        # Verify the query uses $in operator
        find_call_args = mock_q_coll.find.call_args[0][0]
        assert "$in" in str(find_call_args)


class TestBatchReviewUsesUpdateMany:
    """Req 6.3: batch_update_review_status uses update_many"""

    @pytest.mark.asyncio
    async def test_batch_review_uses_update_many(self):
        """Verify update_many() is called with $in operator"""
        from app.api.questions import batch_update_review_status
        from app.models.schemas import ReviewStatusBatchUpdate

        q_ids = [str(ObjectId()), str(ObjectId()), str(ObjectId())]
        batch_data = ReviewStatusBatchUpdate(
            question_ids=q_ids,
            review_status="approved",
            feedback="Good job",
        )

        mock_result = MagicMock()
        mock_result.modified_count = 3

        mock_collection = AsyncMock()
        mock_collection.update_many = AsyncMock(return_value=mock_result)

        mock_database = MagicMock()
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)

        with patch("app.database.db") as patched_db:
            patched_db.get_db.return_value = mock_database
            result = await batch_update_review_status(batch_data)

        # Verify update_many was called (not individual updates)
        mock_collection.update_many.assert_called_once()

        # Verify $in operator was used
        call_args = mock_collection.update_many.call_args[0]
        filter_query = call_args[0]
        assert "$in" in str(filter_query)

        assert result["modified_count"] == 3
