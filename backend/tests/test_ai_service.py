"""
AI Service 單元測試
測試 AIService 的核心方法：_call_gemini、perform_qa_answer_clustering 等
"""
import inspect
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai_service import AIService


class TestAIServiceBasic:
    """Basic AIService tests"""

    @pytest.mark.asyncio
    async def test_empty_answers_returns_empty_clusters(self):
        """Req 2.4: Empty student_answers returns {"clusters": []}"""
        service = AIService()
        result = await service.perform_qa_answer_clustering(
            student_answers=[],
            teacher_question="test",
            core_concept="test",
        )
        assert result == {"clusters": []}

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_value_error(self):
        """Req 3.3: Empty GEMINI_API_KEY raises ValueError"""
        service = AIService()
        with patch("app.config.settings.GEMINI_API_KEY", ""):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                await service._call_gemini("test prompt")

    def test_all_methods_are_async(self):
        """Req 9.3: All AI methods are async coroutines"""
        service = AIService()
        assert inspect.iscoroutinefunction(service._call_gemini)
        assert inspect.iscoroutinefunction(service.perform_qa_answer_clustering)
        assert inspect.iscoroutinefunction(service.generate_response_draft)
        assert inspect.iscoroutinefunction(service.analyze_question)
        assert inspect.iscoroutinefunction(service.get_reply)


class TestCallGemini:
    """Tests for _call_gemini method"""

    @pytest.mark.asyncio
    async def test_uses_correct_model_name(self):
        """Req 3.1: Uses model name from settings"""
        service = AIService()
        service.api_key = "test-key"
        service.model_name = "gemini-2.0-flash"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "test response"
        mock_client.models.generate_content.return_value = mock_response
        service._client = mock_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await service._call_gemini("test prompt")

        call_args = mock_thread.call_args
        assert call_args is not None
        assert "gemini-2.0-flash" in str(call_args)

    @pytest.mark.asyncio
    async def test_json_mode_sets_response_mime_type(self):
        """Req 3.2: json_mode=True sets response_mime_type to application/json"""
        service = AIService()
        service.api_key = "test-key"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"test": true}'
        mock_client.models.generate_content.return_value = mock_response
        service._client = mock_client

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await service._call_gemini("test", json_mode=True)

        assert result == {"test": True}

    @pytest.mark.asyncio
    async def test_invalid_json_returns_empty_dict(self):
        """Req 3.4: Invalid JSON in json_mode returns {}"""
        service = AIService()
        service.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.text = "not valid json {{"

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await service._call_gemini("test", json_mode=True)

        assert result == {}

    @pytest.mark.asyncio
    async def test_retry_on_429_error(self):
        """Req 11.1: Retries on 429 errors with exponential backoff"""
        service = AIService()
        service.api_key = "test-key"

        mock_response = MagicMock()
        mock_response.text = "success"

        call_count = 0

        async def mock_to_thread(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("429 Too Many Requests")
            return mock_response

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch("app.config.settings.GEMINI_RETRY_MAX_ATTEMPTS", 3):
                    with patch("app.config.settings.GEMINI_RETRY_BASE_DELAY", 0.01):
                        result = await service._call_gemini("test")

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self):
        """Req 11.2: Timeout raises asyncio.TimeoutError"""
        service = AIService()
        service.api_key = "test-key"

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await service._call_gemini("test")

    @pytest.mark.asyncio
    async def test_all_retries_fail_raises_runtime_error(self):
        """Req 11.3: All retries failing raises RuntimeError"""
        service = AIService()

        async def always_fail(*args, **kwargs):
            raise Exception("503 Service Unavailable")

        with patch("asyncio.to_thread", side_effect=always_fail):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch("app.config.settings.GEMINI_RETRY_MAX_ATTEMPTS", 3):
                    with patch("app.config.settings.GEMINI_RETRY_BASE_DELAY", 0.01):
                        with pytest.raises(RuntimeError):
                            await service._call_gemini("test")

    @pytest.mark.asyncio
    async def test_retry_logs_attempt_number(self):
        """Req 11.4: Retry logs attempt number"""
        service = AIService()
        service.api_key = "test-key"

        call_count = 0

        async def fail_then_succeed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("429 Rate Limited")
            mock_resp = MagicMock()
            mock_resp.text = "ok"
            return mock_resp

        with patch("asyncio.to_thread", side_effect=fail_then_succeed):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch("app.config.settings.GEMINI_RETRY_MAX_ATTEMPTS", 3):
                    with patch("app.config.settings.GEMINI_RETRY_BASE_DELAY", 0.01):
                        with patch("app.services.ai_service.logger") as mock_logger:
                            result = await service._call_gemini("test")

        assert result == "ok"
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args_list[0]
        assert "1/3" in str(warning_call) or "重試" in str(warning_call)
