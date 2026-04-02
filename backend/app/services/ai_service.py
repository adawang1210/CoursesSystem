"""
AI 服務模組
主要使用 Google Gemini API，當 Gemini 不可用時自動切換至 Groq 備援
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from ..config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client = None
        self._groq_client = None

    def _get_client(self) -> genai.Client:
        """取得或建立 Gemini Client 實例"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("系統設定錯誤：缺少 GEMINI_API_KEY")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _get_groq_client(self):
        """取得或建立 Groq Client 實例"""
        if self._groq_client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("系統設定錯誤：缺少 GROQ_API_KEY")
            from groq import Groq
            self._groq_client = Groq(api_key=settings.GROQ_API_KEY)
        return self._groq_client

    async def _call_gemini(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> Any:
        """
        非同步 Gemini API 呼叫，含重試與逾時機制
        """
        if not self.api_key:
            raise ValueError("系統設定錯誤：缺少 GEMINI_API_KEY")

        client = self._get_client()

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=2048,
        )
        if json_mode:
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )

        max_attempts = settings.GEMINI_RETRY_MAX_ATTEMPTS
        base_delay = settings.GEMINI_RETRY_BASE_DELAY
        timeout = settings.GEMINI_TIMEOUT_SECONDS

        for attempt in range(max_attempts):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    ),
                    timeout=timeout,
                )

                content = response.text.strip()

                if json_mode:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        logger.error("JSON 解析失敗，原始內容: %s", content)
                        return {}

                return content

            except asyncio.TimeoutError:
                logger.error("Gemini API 呼叫逾時 (超過 %s 秒)", timeout)
                raise

            except Exception as e:
                error_str = str(e)
                is_retryable = "429" in error_str or "503" in error_str
                if is_retryable and attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Gemini API 重試 %d/%d，錯誤: %s，等待 %.1f 秒",
                        attempt + 1, max_attempts, error_str, delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    logger.error("Gemini API 配額已用盡: %s", error_str)
                    raise RuntimeError("Gemini 配額已用盡")

                logger.error("Gemini AI 呼叫失敗: %s", error_str)
                return None

        logger.error("Gemini API 所有 %d 次重試均失敗", max_attempts)
        return None

    async def _call_groq(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> Any:
        """
        Groq API 呼叫（OpenAI 相容格式）
        使用 llama-3.1-70b-versatile 作為備援模型
        """
        client = self._get_groq_client()
        model = settings.GROQ_MODEL

        logger.info("🔄 使用 Groq 備援模型: %s", model)

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 2048,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await asyncio.to_thread(
                client.chat.completions.create, **kwargs
            )
            content = response.choices[0].message.content.strip()

            if json_mode:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.error("Groq JSON 解析失敗，原始內容: %s", content)
                    return {}

            return content

        except Exception as e:
            logger.error("Groq AI 呼叫失敗: %s", str(e))
            return None

    async def _call_ai(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> Any:
        """
        統一 AI 呼叫入口：先嘗試 Gemini，失敗時自動切換至 Groq 備援
        """
        # 嘗試 Gemini
        try:
            result = await self._call_gemini(prompt, json_mode, temperature)
            if result is not None:
                logger.info("✅ 使用 Gemini (%s) 完成請求", self.model_name)
                return result
            logger.warning("Gemini 回傳 None，嘗試 Groq 備援")
        except RuntimeError as e:
            # 配額用盡等不可恢復錯誤
            logger.warning("Gemini 不可用 (%s)，嘗試 Groq 備援", str(e))
        except Exception as e:
            logger.warning("Gemini 發生錯誤 (%s)，嘗試 Groq 備援", str(e))

        # 嘗試 Groq 備援
        if not settings.GROQ_ENABLED or not settings.GROQ_API_KEY:
            raise RuntimeError("AI 服務配額已用盡，且 Groq 備援未設定。請稍後再試或升級 API 方案。")

        result = await self._call_groq(prompt, json_mode, temperature)
        if result is not None:
            logger.info("✅ 使用 Groq (%s) 備援完成請求", settings.GROQ_MODEL)
            return result

        raise RuntimeError("所有 AI 服務均不可用（Gemini + Groq 皆失敗）")

    async def get_reply(self, user_message: str, system_prompt: str = None) -> str:
        """一般對話回覆（給 LINE Bot 直接回話用）"""
        if not system_prompt:
            system_prompt = "你是一個熱心的教學助理，請用繁體中文回答學生的問題。"

        prompt = f"{system_prompt}\n\n學生訊息：{user_message}"
        try:
            result = await self._call_ai(prompt)
            return result if result else "系統忙碌中，請稍後再試。"
        except RuntimeError:
            return "系統忙碌中，請稍後再試。"

    async def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """深度分析提問，回傳結構化 JSON"""
        prompt = """你是一個教育數據分析師。請分析學生的提問，並回傳嚴格的 JSON 格式資料。
欄位說明：
- keywords: (list) 3-5個關鍵字
- difficulty_score: (float) 0.0(最簡單)-1.0(最困難)
- sentiment: (str) positive/neutral/negative
- summary: (str) 20字以內的問題摘要

學生提問：""" + question_text

        try:
            result = await self._call_ai(prompt, json_mode=True, temperature=0.3)
        except RuntimeError:
            result = None
        if not result:
            return {"keywords": [], "difficulty_score": 0.0, "sentiment": "neutral", "summary": "分析失敗"}
        return result

    async def generate_response_draft(self, question_text: str) -> str:
        """生成教學回覆草稿"""
        prompt = """你是一位資深的教學助理。請針對學生的問題撰寫一份回覆草稿。
要求：
1. 語氣親切、鼓勵學生
2. 結構清晰，先回答核心問題，再補充範例或概念
3. 使用繁體中文

學生問題：""" + question_text

        try:
            result = await self._call_ai(prompt, temperature=0.7)
        except RuntimeError:
            result = None
        return result if result else "無法生成草稿"

    async def perform_qa_answer_clustering(
        self,
        student_answers: List[str],
        teacher_question: str,
        core_concept: str,
        expected_misconceptions: Optional[str] = None,
        max_clusters: int = 5,
        existing_topics: List[str] = None
    ) -> Dict[str, Any]:
        """
        根據老師期望的核心觀念與預期迷思，深度診斷並分類學生的理解狀態
        """
        if not student_answers:
            return {"clusters": []}

        indexed_text = "\n".join([f"ID_{i}: {ans[:300]}" for i, ans in enumerate(student_answers)])

        existing_topics_str = ""
        if existing_topics:
            topics_joined = ", ".join([f'"{t}"' for t in existing_topics])
            existing_topics_str = f"\n【現有自訂群組】\n{topics_joined}\n(請務必優先將符合的回答歸入這些群組中，並嚴格保持「群組標籤」名稱完全一致)\n"

        misconceptions_str = ""
        if expected_misconceptions:
            misconceptions_str = f"- 老師預期探測的迷思/分析重點：{expected_misconceptions}\n"

        prompt = f"""你是一位專業的「教育診斷分析師」。老師出了一道探究型的問答題，並提供了期望學生掌握的「核心觀念」。
你的任務不是單純批改對錯，而是要「深度診斷」以下學生的作答，將具有「相似理解類型」、「相同認知盲點」或「相似迷思」的回答進行分群聚類。

⚠️ 所有群組標籤與摘要必須使用繁體中文。

【電子商務領域指引】
本課程涉及電子商務主題，學生回答可能涉及台灣常見電商平台（蝦皮、momo、PChome、博客來等）及相關概念（B2C、C2C、跨境電商、物流金流、數位行銷等）。請在分群時考慮電商領域的專業知識脈絡。

【教學與診斷資訊】
- 老師的提問：{teacher_question}
- 期望的核心觀念：{core_concept}
{misconceptions_str}
{existing_topics_str}

【任務規則】
1. **診斷導向分群**：請跳脫死板的對/錯，分類標籤必須精準描述學生的「認知狀態」或「思考特徵」。（例如：「具備完整因果推論」、「混淆了A與B的概念」、「只背誦專有名詞未理解本質」、「依賴直覺經驗取代科學概念」等）。
2. **群組數量**：請將學生的回答分成合適的群組（包含現有自訂群組與你新增的群組），總群組數請盡量控制在 {max_clusters} 個以內。
3. **強制覆蓋 (重要)**：列表中的「每一個」學生的回答都必須被分配到某個群組中 (Index 0 到 {len(student_answers)-1})，絕不能遺漏。

4. **格式要求**：請回傳嚴格的 JSON 格式，格式如下：
{{
    "clusters": [
        {{
            "topic_label": "群組標籤 (例如：具備完整因果推論 / 混淆了供需法則的因果)",
            "summary": "此群組的診斷總結 (詳細說明這群學生目前的理解走到哪一步，以及共同的盲點或迷思是什麼)",
            "question_indices": [0, 2, 5]
        }}
    ]
}}

請對以下學生的回答進行教育診斷與分群：
{indexed_text}"""

        result = await self._call_ai(prompt, json_mode=True, temperature=0.5)

        if not result:
            return {"clusters": []}

        return result


# 建立全域實例
ai_service = AIService()
