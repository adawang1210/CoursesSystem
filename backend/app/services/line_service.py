"""
LINE 服務邏輯層
負責處理 LINE Bot 的訊息判斷、課程綁定與提問記錄
"""
import traceback
import asyncio
from datetime import datetime
from bson import ObjectId
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    FollowEvent
)

from ..config import settings
from ..database import db
from ..utils.security import generate_pseudonym
from ..models.schemas import QuestionCreate
from .question_service import question_service

class LineService:
    def __init__(self):
        self.configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)

    async def _reply_text(self, reply_token: str, text: str):
        """共用的回覆文字訊息方法"""
        if not settings.LINE_CHANNEL_ACCESS_TOKEN:
            print("⚠️ LINE_CHANNEL_ACCESS_TOKEN 未設定，無法回覆訊息")
            return

        try:
            async with AsyncApiClient(self.configuration) as api_client:
                line_bot_api = AsyncMessagingApi(api_client)
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=text)]
                    )
                )
        except Exception as e:
            print(f"❌ 傳送 LINE 回覆失敗: {str(e)}")

    async def handle_follow(self, event: FollowEvent):
        """處理加入好友事件"""
        welcome_msg = (
            "👋 歡迎使用 AI 跨領域教學輔助機器人！\n\n"
            "請先輸入「綁定 [課程代碼]」來加入您的課程。\n"
            "例如：「綁定 65d4a1b2c3d4e5f6g7h8i9j0」\n"
            "（請向您的授課教師索取專屬課程代碼）\n\n"
            "💡 綁定成功後，您在這裡發送的所有問題，都會以「匿名」的方式收集給老師，請放心且大膽地提問喔！"
        )
        await self._reply_text(event.reply_token, welcome_msg)

    async def handle_postback(self, event: PostbackEvent):
        """處理按鈕回傳事件 (預留擴充)"""
        pass

    async def handle_text_message(self, event: MessageEvent):
        """處理文字訊息的主邏輯 (路由判斷)"""
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        reply_token = event.reply_token
        
        database = db.get_db()

        # 1. 記錄這則收到的原始訊息 (Log 用於統計與除錯)
        pseudonym = generate_pseudonym(user_id)
        await database["line_messages"].insert_one({
            "user_id": user_id,
            "pseudonym": pseudonym,
            "message_type": "text",
            "direction": "received",
            "content": message_text,
            "line_message_id": event.message.id,
            "reply_token": reply_token,
            "created_at": datetime.utcnow()
        })

        # 2. 判斷是否為「系統指令」
        if message_text.startswith("綁定 "):
            await self._handle_bind_course(user_id, message_text, reply_token)
            return
            
        if message_text == "解除綁定":
            await self._handle_unbind_course(user_id, reply_token)
            return

        # 3. 若不是指令，則視為「一般提問」
        # 🔥 修改：傳入 event.message.id 以便完整寫入資料庫
        await self._handle_question(user_id, pseudonym, message_text, reply_token, event.message.id)

    async def _handle_bind_course(self, user_id: str, message_text: str, reply_token: str):
        """處理綁定課程邏輯"""
        database = db.get_db()
        
        # 拆解指令，例如 "綁定 65d4a1b2..."
        parts = message_text.split(" ", 1)
        if len(parts) < 2:
            await self._reply_text(reply_token, "⚠️ 格式錯誤。請輸入「綁定 [課程代碼]」。")
            return
            
        course_code = parts[1].strip()
        
        # 尋找課程
        course = None
        try:
            # 先假設老師給的是資料庫的 ObjectId
            course = await database["courses"].find_one({"_id": ObjectId(course_code)})
        except:
            # 容錯處理：如果輸入的不是合法 ID 格式，改用課程名稱去配對
            course = await database["courses"].find_one({"course_name": course_code})
            
        if not course:
            await self._reply_text(reply_token, f"❌ 找不到代碼為「{course_code}」的課程。請向助教或老師確認正確的代碼喔！")
            return

        # 更新或新增該使用者的綁定狀態到 line_users 表
        await database["line_users"].update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "current_course_id": str(course["_id"]),
                "current_course_name": course["course_name"],
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )

        reply_msg = f"✅ 綁定成功！\n您已成功加入「{course['course_name']}」。\n\n現在起，您可以直接把不懂的地方打字傳上來，系統會自動幫您記錄喔！"
        await self._reply_text(reply_token, reply_msg)

    async def _handle_unbind_course(self, user_id: str, reply_token: str):
        """處理解除綁定邏輯"""
        database = db.get_db()
        await database["line_users"].update_one(
            {"user_id": user_id},
            {"$set": {"current_course_id": None, "current_course_name": None, "updated_at": datetime.utcnow()}}
        )
        await self._reply_text(reply_token, "👋 已為您解除綁定。若有其他課程的問題，請重新輸入綁定指令。")

    # 🔥 修改：接收 message_id
    async def _handle_question(self, user_id: str, pseudonym: str, message_text: str, reply_token: str, message_id: str):
        """處理學生提問邏輯 (寫入資料庫供 AI 聚類)"""
        database = db.get_db()
        
        # 檢查該使用者目前是否有綁定課程
        user_data = await database["line_users"].find_one({"user_id": user_id})
        
        if not user_data or not user_data.get("current_course_id"):
            await self._reply_text(reply_token, "⚠️ 您尚未綁定任何課程！\n請先輸入「綁定 [課程代碼]」來告訴我您要問哪堂課的問題。")
            return

        course_id = user_data["current_course_id"]
        
        try:
            # 🔥 修改：建立 Pydantic 結構
            new_q_data = QuestionCreate(
                course_id=course_id,
                line_user_id=user_id,
                question_text=message_text,
                original_message_id=message_id
            )
            
            # 🔥 直接呼叫 question_service，它會自動處理去識別化與狀態更新
            question_doc = await question_service.create_question(new_q_data)
            
            # 🔥 透過 asyncio 在背景非同步執行 AI 分析，這樣才不會卡住 LINE 的回覆速度！
            asyncio.create_task(
                question_service.process_new_question_ai(question_doc["_id"], message_text)
            )
            
            # 回覆確認訊息給學生
            await self._reply_text(reply_token, "📥 已匿名收到您的提問！\n老師會在課後由 AI 助理協助整理並統一回覆大家。")
            
        except ValueError as ve:
            # 捕捉到課程不存在或停用的錯誤
            await self._reply_text(reply_token, f"❌ 提問失敗：{str(ve)}")
        except Exception as e:
            print(f"❌ 寫入提問失敗: {str(e)}")
            traceback.print_exc()
            await self._reply_text(reply_token, "❌ 系統發生小錯誤，無法儲存您的提問，請稍後再試一次。")

# 建立實例供 router 調用
line_service = LineService()