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

# 共用重試邏輯
async def _retry_with_backoff(
    fn,
    max_attempts: int,
    base_delay: float,
    timeout: float,
    provider: str,
) -> Any:
    """
    通用重試包裝：對 fn() 執行最多 max_attempts 次，遇到 429/503 時指數退避。
    成功時回傳結果；不可恢復錯誤時 raise。
    """
    for attempt in range(max_attempts):
        try:
            return await asyncio.wait_for(fn(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("%s API 呼叫逾時 (超過 %s 秒)", provider, timeout)
            raise
        except Exception as e:
            error_str = str(e)
            is_retryable = "429" in error_str or "503" in error_str
            if is_retryable and attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "%s API 重試 %d/%d，錯誤: %s，等待 %.1f 秒",
                    provider, attempt + 1, max_attempts, error_str, delay,
                )
                await asyncio.sleep(delay)
                continue
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.error("%s API 配額已用盡: %s", provider, error_str)
                raise RuntimeError(f"{provider} 配額已用盡")
            logger.error("%s AI 呼叫失敗: %s", provider, error_str)
            raise RuntimeError(f"{provider} 呼叫失敗: {error_str}")
    raise RuntimeError(f"{provider} API 所有 {max_attempts} 次重試均失敗")


class AIService:
    def __init__(self):
        self._gemini_client = None
        self._groq_client = None
        self._gemini_lock = asyncio.Lock()
        self._groq_lock = asyncio.Lock()

    async def _get_gemini_client(self) -> genai.Client:
        """Thread-safe lazy init for Gemini client（每次讀取最新 key）"""
        async with self._gemini_lock:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                raise ValueError("系統設定錯誤：缺少 GEMINI_API_KEY")
            if self._gemini_client is None:
                self._gemini_client = genai.Client(api_key=api_key)
            return self._gemini_client

    async def _get_groq_client(self):
        """Thread-safe lazy init for Groq client（每次讀取最新 key）"""
        async with self._groq_lock:
            api_key = settings.GROQ_API_KEY
            if not api_key:
                raise ValueError("系統設定錯誤：缺少 GROQ_API_KEY")
            if self._groq_client is None:
                from groq import Groq
                self._groq_client = Groq(api_key=api_key)
            return self._groq_client

    # ── Gemini ──────────────────────────────────────────────

    async def _call_gemini(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> Any:
        """Gemini API 呼叫，含重試與逾時"""
        client = await self._get_gemini_client()
        model = settings.GEMINI_MODEL

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=2048,
            **({"response_mime_type": "application/json"} if json_mode else {}),
        )

        async def _invoke():
            return await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=config,
            )

        response = await _retry_with_backoff(
            _invoke,
            max_attempts=settings.GEMINI_RETRY_MAX_ATTEMPTS,
            base_delay=settings.GEMINI_RETRY_BASE_DELAY,
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            provider="Gemini",
        )

        content = response.text.strip()
        if json_mode:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error("Gemini JSON 解析失敗，原始內容: %s", content)
                return {}
        return content

    # ── Groq ───────────────────────────────────────────────

    async def _call_groq(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> Any:
        """Groq API 呼叫（OpenAI 相容格式），含重試與逾時"""
        client = await self._get_groq_client()
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

        async def _invoke():
            return await asyncio.to_thread(
                client.chat.completions.create, **kwargs
            )

        response = await _retry_with_backoff(
            _invoke,
            max_attempts=settings.GROQ_RETRY_MAX_ATTEMPTS,
            base_delay=settings.GROQ_RETRY_BASE_DELAY,
            timeout=settings.GROQ_TIMEOUT_SECONDS,
            provider="Groq",
        )

        content = response.choices[0].message.content.strip()
        if json_mode:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.error("Groq JSON 解析失敗，原始內容: %s", content)
                return {}
        return content

    # ── 統一入口 ───────────────────────────────────────────

    async def _call_ai(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> Any:
        """先嘗試 Gemini，失敗時自動切換至 Groq 備援"""
        # 嘗試 Gemini
        try:
            result = await self._call_gemini(prompt, json_mode, temperature)
            logger.info("✅ 使用 Gemini (%s) 完成請求", settings.GEMINI_MODEL)
            return result
        except RuntimeError as e:
            logger.warning("Gemini 不可用 (%s)，嘗試 Groq 備援", e)
        except Exception as e:
            logger.warning("Gemini 發生錯誤 (%s)，嘗試 Groq 備援", e)

        # 嘗試 Groq 備援
        if not settings.GROQ_ENABLED or not settings.GROQ_API_KEY:
            raise RuntimeError(
                "AI 服務配額已用盡，且 Groq 備援未設定。請稍後再試或升級 API 方案。"
            )

        try:
            result = await self._call_groq(prompt, json_mode, temperature)
            logger.info("✅ 使用 Groq (%s) 備援完成請求", settings.GROQ_MODEL)
            return result
        except Exception as e:
            raise RuntimeError(f"所有 AI 服務均不可用（Gemini + Groq 皆失敗）: {e}")

    # ── 業務方法 ─────────────────────────────────────────────

    async def get_reply(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """一般對話回覆（給 LINE Bot 直接回話用）"""
        if not system_prompt:
            system_prompt = "你是一個熱心的教學助理，請用繁體中文回答學生的問題。"
        prompt = f"{system_prompt}\n\n學生訊息：{user_message}"
        try:
            return await self._call_ai(prompt)
        except RuntimeError:
            return "系統忙碌中，請稍後再試。"

    async def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """深度分析提問，回傳結構化 JSON"""
        prompt = f"""你是一個教育數據分析師。請分析學生的提問，並回傳嚴格的 JSON 格式資料。
欄位說明：
- keywords: (list) 3-5個關鍵字
- difficulty_score: (float) 0.0(最簡單)-1.0(最困難)
- sentiment: (str) positive/neutral/negative
- summary: (str) 20字以內的問題摘要

學生提問：{question_text}"""
        try:
            result = await self._call_ai(prompt, json_mode=True, temperature=0.3)
        except RuntimeError:
            result = None
        if not result:
            return {"keywords": [], "difficulty_score": 0.0, "sentiment": "neutral", "summary": "分析失敗"}
        return result

    async def generate_response_draft(self, question_text: str) -> str:
        """生成教學回覆草稿"""
        prompt = f"""你是一位資深的教學助理。請針對學生的問題撰寫一份回覆草稿。
要求：
1. 語氣親切、鼓勵學生
2. 結構清晰，先回答核心問題，再補充範例或概念
3. 使用繁體中文

學生問題：{question_text}"""
        try:
            return await self._call_ai(prompt, temperature=0.7)
        except RuntimeError:
            return "無法生成草稿"

    async def perform_qa_answer_clustering(
        self,
        student_answers: List[str],
        teacher_question: str,
        core_concept: str,
        expected_misconceptions: Optional[str] = None,
        max_clusters: int = 5,
        existing_topics: Optional[List[str]] = None,
        domain_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        根據老師期望的核心觀念與預期迷思，深度診斷並分類學生的理解狀態。
        domain_context: 課程領域描述（選填），若未提供則使用預設電商領域指引。
        """
        if not student_answers:
            return {"clusters": []}

        max_chars = settings.AI_ANSWER_MAX_CHARS
        indexed_text = "\n".join(
            [f"ID_{i}: {ans[:max_chars]}" for i, ans in enumerate(student_answers)]
        )

        existing_topics_str = ""
        if existing_topics:
            topics_joined = ", ".join([f'"{t}"' for t in existing_topics])
            existing_topics_str = (
                f"\n【現有自訂群組】\n{topics_joined}\n"
                f"(請務必優先將符合的回答歸入這些群組中，並嚴格保持「群組標籤」名稱完全一致)\n"
            )

        misconceptions_str = ""
        if expected_misconceptions:
            misconceptions_str = f"- 老師預期探測的迷思/分析重點：{expected_misconceptions}\n"

        # 領域指引：可由呼叫端傳入，預設為電商
        if domain_context is None:
            domain_context = (
                "本課程涉及電子商務主題，學生回答可能涉及台灣常見電商平台"
                "（蝦皮、momo、PChome、博客來等）及相關概念"
                "（B2C、C2C、跨境電商、物流金流、數位行銷等）。"
                "請在分群時考慮電商領域的專業知識脈絡。"
            )

        truncation_note = ""
        if any(len(ans) > max_chars for ans in student_answers):
            truncation_note = f"\n⚠️ 部分回答超過 {max_chars} 字元已被截斷，請根據可見內容進行判斷。\n"

        prompt = f"""你是一位專業的「教育診斷分析師」。老師出了一道探究型的問答題，並提供了期望學生掌握的「核心觀念」。
你的任務不是單純批改對錯，而是要「深度診斷」以下學生的作答，將具有「相似理解類型」、「相同認知盲點」或「相似迷思」的回答進行分群聚類。

⚠️ 所有群組標籤與摘要必須使用繁體中文。

【領域指引】
{domain_context}

【教學與診斷資訊】
- 老師的提問：{teacher_question}
- 期望的核心觀念：{core_concept}
{misconceptions_str}
{existing_topics_str}
{truncation_note}
【任務規則】
1. **診斷導向分群**：請跳脫死板的對/錯，分類標籤必須精準描述學生的「認知狀態」或「思考特徵」。（例如：「具備完整因果推論」、「混淆了A與B的概念」、「只背誦專有名詞未理解本質」、「依賴直覺經驗取代科學概念」等）。
2. **群組數量**：請將學生的回答分成合適的群組（包含現有自訂群組與你新增的群組），總群組數請盡量控制在 {max_clusters} 個以內。
3. **強制覆蓋 (重要)**：列表中的「每一個」學生的回答都必須被分配到某個群組中 (Index 0 到 {len(student_answers)-1})，絕不能遺漏。
4. **短答不等於無效 (極重要)**：許多學生會用非常簡短的方式作答（例如只列出名稱、關鍵字、或用逗號/數字分隔的清單）。只要回答的內容與老師的提問主題相關，就必須視為有效作答並歸入對應的認知群組。只有完全離題、開玩笑、打招呼、或明顯無意義的內容（例如「555」、「水喔」、「愚人節快樂」、純問候語）才能歸入「無效回答」類別。
5. **格式要求**：請回傳嚴格的 JSON 格式，格式如下：
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
