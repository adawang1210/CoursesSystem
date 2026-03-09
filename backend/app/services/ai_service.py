import requests
import json
from typing import List, Dict, Any, Optional
from ..config import settings

class AIService:
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        # 確保網址結尾正確
        base_url = settings.AI_BASE_URL.rstrip('/')
        self.api_url = f"{base_url}/chat/completions"

    def _call_ai_api(self, messages: List[Dict[str, str]], json_mode: bool = False, temperature: float = 0.7) -> Any:
        """
        內部共用的 API 呼叫邏輯
        """
        if not self.api_key:
            raise ValueError("系統設定錯誤：缺少 AI API Key")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1024
        }

        # 如果需要 JSON 格式 (Groq/OpenAI 支援)
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=30 # 分析任務可能需要久一點，建議設 30秒
            )
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()

            if json_mode:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"❌ JSON 解析失敗，原始內容: {content}")
                    return {}
            
            return content

        except requests.exceptions.Timeout:
            print("❌ AI 回應超時")
            return None
        except Exception as e:
            print(f"❌ AI 呼叫失敗: {str(e)}")
            return None

    def get_reply(self, user_message: str, system_prompt: str = None) -> str:
        """
        [原有功能] 一般對話回覆 (給 LINE Bot 直接回話用)
        """
        if not system_prompt:
            system_prompt = "你是一個熱心的教學助理，請用繁體中文回答學生的問題。"
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        result = self._call_ai_api(messages)
        return result if result else "系統忙碌中，請稍後再試。"

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """
        [原有功能] 深度分析提問
        """
        system_prompt = """
        你是一個教育數據分析師。請分析學生的提問，並回傳嚴格的 JSON 格式資料。
        欄位說明：
        - keywords: (list) 3-5個關鍵字
        - difficulty_score: (float) 0.0(最簡單)-1.0(最困難)
        - sentiment: (str) positive/neutral/negative
        - summary: (str) 20字以內的問題摘要
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"學生提問：{question_text}"}
        ]
        
        result = self._call_ai_api(messages, json_mode=True, temperature=0.3)
        if not result:
            return {"keywords": [], "difficulty_score": 0.0, "sentiment": "neutral", "summary": "分析失敗"}
        return result

    def generate_response_draft(self, question_text: str) -> str:
        """
        [原有功能] 生成教學回覆草稿
        """
        system_prompt = """
        你是一位資深的教學助理。請針對學生的問題撰寫一份回覆草稿。
        要求：
        1. 語氣親切、鼓勵學生
        2. 結構清晰，先回答核心問題，再補充範例或概念
        3. 使用繁體中文
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question_text}
        ]
        
        result = self._call_ai_api(messages, temperature=0.7)
        return result if result else "無法生成草稿"

    # =========== 🔥 核心升級：針對 Q&A 回答的批閱式聚類 ===========
    def perform_qa_answer_clustering(
        self, 
        student_answers: List[str], 
        teacher_question: str,
        standard_answer: str,
        max_clusters: int = 5
    ) -> Dict[str, Any]:
        """
        [全新功能] 根據老師的題目與標準答案，批閱並分類學生的回答
        """
        if not student_answers:
            return {"clusters": []}

        # 1. 幫學生的回答加上索引編號
        indexed_text = "\n".join([f"ID_{i}: {ans[:300]}" for i, ans in enumerate(student_answers)])
        
        # 2. 設計批閱與分群專用的 Prompt
        system_prompt = f"""
        你是一位專業的大學課程助教。老師出了一道課堂問答題，並提供了標準答案。
        請根據「題目」與「標準答案」，批閱以下學生的作答，並將具有「相似理解程度」、「相同迷思概念」或「相似錯誤」的回答進行分群聚類。

        【題目資訊】
        - 老師的提問：{teacher_question}
        - 期望的標準答案：{standard_answer}

        【任務規則】
        1. **概念分群**：請依據學生的理解程度分類（例如：「觀念完全正確」、「部分正確：缺少XX概念」、「嚴重迷思：誤解YY」等）。
        2. **群組數量**：請將學生的回答分成 1 到 {max_clusters} 個群組。
        3. **強制覆蓋 (重要)**：列表中的「每一個」學生的回答都必須被分配到某個群組中 (Index 0 到 {len(student_answers)-1})，絕不能遺漏任何一個學生。
        
        4. **格式要求**：請回傳嚴格的 JSON 格式，格式如下：
        {{
            "clusters": [
                {{
                    "topic_label": "群組標籤 (例如：觀念完全正確 / 忽略了成本考量)",
                    "summary": "此群組的批閱總結 (簡述這群學生的共同理解特徵或盲點)",
                    "question_indices": [0, 2, 5] // 對應原始作答列表的索引 (整數)
                }}
            ]
        }}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"請對以下學生的回答進行批閱與分群：\n{indexed_text}"}
        ]

        # 呼叫 LLM
        result = self._call_ai_api(messages, json_mode=True, temperature=0.5) # 稍微調低溫度以求準確分類
        
        if not result:
            return {"clusters": []}
            
        return result
    # ==========================================================

# 建立全域實例
ai_service = AIService()