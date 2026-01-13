import requests
import json
from ..config import settings

class AIService:
    def __init__(self):
        self.api_key = settings.AI_API_KEY
        self.model = settings.AI_MODEL
        self.api_url = settings.AI_BASE_URL + "/chat/completions"

    def get_reply(self, user_message: str, system_prompt: str = None) -> str:
        """
        統一處理與 AI 的溝通邏輯
        """
        if not self.api_key:
            return "系統設定錯誤：缺少 AI API Key"

        if not system_prompt:
            system_prompt = "你是一個熱心的教學助理，請用繁體中文回答學生的問題。"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 500  # 限制回應長度，避免 token 爆炸
        }

        try:
            response = requests.post(
                self.api_url, 
                json=payload, 
                headers=headers, 
                timeout=15 # 設定超時，避免 LINE等待過久
            )
            response.raise_for_status() # 檢查是否有 HTTP 錯誤
            
            data = response.json()
            return data['choices'][0]['message']['content'].strip()

        except requests.exceptions.Timeout:
            print("❌ AI 回應超時")
            return "AI 思考太久了，請稍後再試，或換個簡單一點的問題。"
        except Exception as e:
            print(f"❌ AI 呼叫失敗: {str(e)}")
            return "目前 AI 服務暫時無法使用，已通知管理員。"

# 建立一個全域實例供其他檔案呼叫
ai_service = AIService()