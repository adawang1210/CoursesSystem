"""
AI 服務模組
使用 Google Gemini API（google-genai SDK）提供 AI 聚類分析、回覆草稿生成等功能
"""
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from ..config import settings


class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client = None

    def _get_client(self) -> genai.Client:
        """取得或建立 Gemini Client 實例"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("系統設定錯誤：缺少 GEMINI_API_KEY")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _call_gemini(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> Any:
        """
        內部共用的 Gemini API 呼叫邏輯

        Args:
            prompt: 完整的提示文字（含系統指令與使用者輸入）
            json_mode: 是否要求回傳 JSON 格式
            temperature: 生成溫度
        Returns:
            str 或 dict（json_mode=True 時）或 None（失敗時）
        """
        if not self.api_key:
            raise ValueError("系統設定錯誤：缺少 GEMINI_API_KEY")

        try:
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

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

            content = response.text.strip()

            if json_mode:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"❌ JSON 解析失敗，原始內容: {content}")
                    return {}

            return content

        except Exception as e:
            print(f"❌ Gemini AI 呼叫失敗: {str(e)}")
            return None

    def get_reply(self, user_message: str, system_prompt: str = None) -> str:
        """
        一般對話回覆（給 LINE Bot 直接回話用）
        """
        if not system_prompt:
            system_prompt = "你是一個熱心的教學助理，請用繁體中文回答學生的問題。"

        prompt = f"{system_prompt}\n\n學生訊息：{user_message}"
        result = self._call_gemini(prompt)
        return result if result else "系統忙碌中，請稍後再試。"

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """
        深度分析提問，回傳結構化 JSON
        """
        prompt = """你是一個教育數據分析師。請分析學生的提問，並回傳嚴格的 JSON 格式資料。
欄位說明：
- keywords: (list) 3-5個關鍵字
- difficulty_score: (float) 0.0(最簡單)-1.0(最困難)
- sentiment: (str) positive/neutral/negative
- summary: (str) 20字以內的問題摘要

學生提問：""" + question_text

        result = self._call_gemini(prompt, json_mode=True, temperature=0.3)
        if not result:
            return {"keywords": [], "difficulty_score": 0.0, "sentiment": "neutral", "summary": "分析失敗"}
        return result

    def generate_response_draft(self, question_text: str) -> str:
        """
        生成教學回覆草稿
        """
        prompt = """你是一位資深的教學助理。請針對學生的問題撰寫一份回覆草稿。
要求：
1. 語氣親切、鼓勵學生
2. 結構清晰，先回答核心問題，再補充範例或概念
3. 使用繁體中文

學生問題：""" + question_text

        result = self._call_gemini(prompt, temperature=0.7)
        return result if result else "無法生成草稿"

    def perform_qa_answer_clustering(
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

        result = self._call_gemini(prompt, json_mode=True, temperature=0.5)

        if not result:
            return {"clusters": []}

        return result


# 建立全域實例
ai_service = AIService()
