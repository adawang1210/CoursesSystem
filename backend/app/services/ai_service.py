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
        [新增功能] 深度分析提問
        回傳：關鍵字、難度評分、情緒分析、摘要
        """
        system_prompt = """
        你是一個教育數據分析師。請分析學生的提問，並回傳嚴格的 JSON 格式資料。
        欄位說明：
        - keywords: (list) 3-5個關鍵字
        - difficulty_score: (float) 0.0(最簡單)-1.0(最困難)
        - sentiment: (str) positive/neutral/negative
        - summary: (str) 20字以內的問題摘要
        
        範例輸出：
        {
            "keywords": ["迴圈", "Python", "錯誤處理"],
            "difficulty_score": 0.3,
            "sentiment": "neutral",
            "summary": "詢問 Python 迴圈語法錯誤"
        }
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"學生提問：{question_text}"}
        ]
        
        # 呼叫 API 並強制 JSON 模式
        result = self._call_ai_api(messages, json_mode=True, temperature=0.3)
        
        # 如果失敗回傳預設值
        if not result:
            return {
                "keywords": [],
                "difficulty_score": 0.0,
                "sentiment": "neutral",
                "summary": "分析失敗"
            }
        return result

    def generate_response_draft(self, question_text: str) -> str:
        """
        [新增功能] 生成教學回覆草稿
        """
        system_prompt = """
        你是一位資深的教學助理。請針對學生的問題撰寫一份回覆草稿。
        要求：
        1. 語氣親切、鼓勵學生
        2. 結構清晰，先回答核心問題，再補充範例或概念
        3. 使用繁體中文
        4. 如果問題不明確，請引導學生澄清
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question_text}
        ]
        
        result = self._call_ai_api(messages, temperature=0.7)
        return result if result else "無法生成草稿"

    def generate_cluster_label(self, questions: List[str]) -> Dict[str, Any]:
        """
        [新增功能] 為一群相似問題產生主題標籤
        """
        questions_text = "\n".join([f"- {q}" for q in questions[:10]]) # 取前10個避免 Token 爆炸
        
        system_prompt = """
        你是一個課程管理者。以下是一群相似的學生提問，請歸納出一個共同的主題。
        請回傳 JSON 格式：
        {
            "topic_label": "主題名稱 (5-10字)",
            "summary": "這群問題的綜合摘要 (50字以內)"
        }
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"問題列表：\n{questions_text}"}
        ]
        
        result = self._call_ai_api(messages, json_mode=True)
        
        if not result:
            return {"topic_label": "未命名主題", "summary": ""}
        return result
    
    def perform_advanced_clustering(
        self, 
        questions: List[str], 
        max_new_topics: int = 5,  # 🔥 改名：這裡接收的是「還能新增幾個」
        existing_topics: List[str] = None
    ) -> Dict[str, Any]:
        """
        [進階版] 讓 AI 針對輸入的問題列表進行「多主題拆分」
        :param max_new_topics: 允許新增的全新主題數量 (已扣除既有主題)
        :param existing_topics: 既有主題列表 (AI 應優先使用)
        """
        if not questions:
            return {"clusters": []}

        # 1. 幫問題加上索引編號
        indexed_text = "\n".join([f"ID_{i}: {q[:200]}" for i, q in enumerate(questions)])
        
        # 2. 動態建構既有主題 context
        topic_context = ""
        if existing_topics and len(existing_topics) > 0:
            topics_str = "、".join(existing_topics)
            topic_context = f"""
            3. **既有主題清單**：目前資料庫已有以下主題：【{topics_str}】。
               - 請 **優先** 將問題歸類到上述既有主題中。
               - 歸類到既有主題 **不消耗** 新增額度。
            """

        # 3. 使用 f-string 注入 max_new_topics 變數
        system_prompt = f"""
        你是一個精準的提問分類系統。請分析使用者的問題列表並進行歸類。
        
        規則：
        1. **優先歸類**：請優先檢查問題是否屬於「既有主題」。
        2. **新增限制**：如果問題真的無法歸入既有主題，你可以建立新的主題，但 **最多只能建立 {max_new_topics} 個全新的主題**。
           - 如果新增額度用完，請將剩餘問題歸入「其他」或強制併入最接近的既有主題。
        {topic_context}
        4. **合併策略**：請積極合併語意相似的主題 (例如：'Python 迴圈' 與 'For Loop' 應合併)。
        5. 🔥 **強制覆蓋 (重要)**：**列表中的「每一個」問題都必須被分配到某個群組中 (Index 0 到 {len(questions)-1})，不能有遺漏。**
           - 請確保回傳的 JSON 中，所有問題的 Index 都有出現。
        
        6. **格式要求**：請回傳嚴格的 JSON 格式，不要包含 Markdown 標記。格式如下：
        {{
            "clusters": [
                {{
                    "topic_label": "主題名稱 (5-10字)",
                    "summary": "主題摘要 (簡述該群組包含的問題類型)",
                    "question_indices": [0, 2, 5] // 對應原始列表的索引 (整數)
                }}
            ]
        }}
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"請對以下問題進行分類：\n{indexed_text}"}
        ]

        # 呼叫 LLM
        result = self._call_ai_api(messages, json_mode=True)
        
        if not result:
            return {"clusters": []}
            
        return result

# 建立全域實例
ai_service = AIService()