"""
資料庫索引驗證測試
驗證 ensure_indexes 呼叫正確的 create_index 方法
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestEnsureIndexes:
    """Req 7.1, 7.2, 7.3, 7.4: Verify ensure_indexes creates all expected indexes"""

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates_all_indexes(self):
        """Verify create_index is called for all expected indexes"""
        from app.database import Database

        mock_questions = AsyncMock()
        mock_clusters = AsyncMock()
        mock_qas = AsyncMock()
        mock_line_users = AsyncMock()

        def get_collection(name):
            collections = {
                "questions": mock_questions,
                "clusters": mock_clusters,
                "qas": mock_qas,
                "line_users": mock_line_users,
            }
            return collections.get(name, AsyncMock())

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch.object(Database, "get_db", return_value=mock_db):
            await Database.ensure_indexes()

        # Req 7.1: questions collection indexes
        questions_calls = mock_questions.create_index.call_args_list
        questions_index_args = [str(c) for c in questions_calls]
        assert any("course_id" in a for a in questions_index_args)
        assert any("reply_to_qa_id" in a for a in questions_index_args)
        assert any("cluster_id" in a for a in questions_index_args)
        assert any("review_status" in a for a in questions_index_args)
        # Compound index
        assert any("pseudonym" in a and "reply_to_qa_id" in a for a in questions_index_args)

        # Req 7.2: clusters collection indexes
        clusters_calls = mock_clusters.create_index.call_args_list
        clusters_index_args = [str(c) for c in clusters_calls]
        assert any("course_id" in a for a in clusters_index_args)
        assert any("qa_id" in a for a in clusters_index_args)
        # Compound index
        assert any("course_id" in a and "qa_id" in a for a in clusters_index_args)

        # Req 7.3: qas collection indexes
        qas_calls = mock_qas.create_index.call_args_list
        qas_index_args = [str(c) for c in qas_calls]
        assert any("course_id" in a for a in qas_index_args)
        # Compound index with allow_replies and expires_at
        assert any("allow_replies" in a and "expires_at" in a for a in qas_index_args)

        # Req 7.4: line_users collection indexes
        line_users_calls = mock_line_users.create_index.call_args_list
        line_users_index_args = [str(c) for c in line_users_calls]
        assert any("current_course_id" in a for a in line_users_index_args)

    @pytest.mark.asyncio
    async def test_ensure_indexes_correct_count(self):
        """Verify the correct number of indexes are created per collection"""
        from app.database import Database

        mock_questions = AsyncMock()
        mock_clusters = AsyncMock()
        mock_qas = AsyncMock()
        mock_line_users = AsyncMock()

        def get_collection(name):
            collections = {
                "questions": mock_questions,
                "clusters": mock_clusters,
                "qas": mock_qas,
                "line_users": mock_line_users,
            }
            return collections.get(name, AsyncMock())

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)

        with patch.object(Database, "get_db", return_value=mock_db):
            await Database.ensure_indexes()

        # questions: course_id, reply_to_qa_id, cluster_id, review_status, compound(reply_to_qa_id, pseudonym) = 5
        assert mock_questions.create_index.call_count == 5

        # clusters: course_id, qa_id, compound(course_id, qa_id) = 3
        assert mock_clusters.create_index.call_count == 3

        # qas: course_id, compound(course_id, allow_replies, expires_at) = 2
        assert mock_qas.create_index.call_count == 2

        # line_users: current_course_id = 1
        assert mock_line_users.create_index.call_count == 1
