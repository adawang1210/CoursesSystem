"""
LINE 服務邏輯層
負責處理 LINE Bot 的訊息判斷、課程綁定與提問記錄
"""
import traceback
import asyncio
from datetime import datetime, timedelta
from bson import ObjectId
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage,
    MulticastRequest
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

    async def broadcast_qa_to_course(self, course_id: str, qa_data: dict):
        """將 Q&A 推播給該課程的所有學生"""
        if not settings.LINE_CHANNEL_ACCESS_TOKEN:
            print("⚠️ LINE_CHANNEL_ACCESS_TOKEN 未設定，無法推播")
            return

        database = db.get_db()
        
        cursor = database["line_users"].find({"current_course_id": course_id})
        users = await cursor.to_list(length=None)
        
        user_ids = [u["user_id"] for u in users if "user_id" in u]
        
        if not user_ids:
            print(f"課程 {course_id} 目前沒有綁定的學生，略過推播")
            return

        text = f"📢 【課堂 Q&A 推播】\n\n❓ 問題：\n{qa_data.get('question')}"
        
        # =========== 🔥 修改 1：區分「限時互動」與「不限時互動」的推播文案 ===========
        if qa_data.get("allow_replies"):
            if qa_data.get("duration_minutes"):
                text += f"\n\n⏳ 老師已開啟限時任務！\n請在 {qa_data.get('duration_minutes')} 分鐘內直接在此回覆您的想法或答案。"
            else:
                text += f"\n\n📝 老師已發布課後互動任務！\n請直接在此回覆您的想法或答案（本任務不限時，直到老師關閉為止）。"
        else:
            text += f"\n\n💡 參考解答：\n{qa_data.get('answer')}"
        # ======================================================================
        
        batch_size = 500
        try:
            async with AsyncApiClient(self.configuration) as api_client:
                line_bot_api = AsyncMessagingApi(api_client)
                
                for i in range(0, len(user_ids), batch_size):
                    batch_user_ids = user_ids[i:i+batch_size]
                    await line_bot_api.multicast(
                        MulticastRequest(
                            to=batch_user_ids,
                            messages=[TextMessage(text=text)]
                        )
                    )
            print(f"✅ 成功推播 Q&A 給 {len(user_ids)} 位學生")
        except Exception as e:
            print(f"❌ 推播 Q&A 失敗: {str(e)}")
            traceback.print_exc()

    async def broadcast_announcement_to_course(self, course_id: str, announcement_data: dict):
        """將課堂公告推播給該課程的所有學生"""
        if not settings.LINE_CHANNEL_ACCESS_TOKEN:
            print("⚠️ LINE_CHANNEL_ACCESS_TOKEN 未設定，無法推播公告")
            return

        database = db.get_db()
        
        cursor = database["line_users"].find({"current_course_id": course_id})
        users = await cursor.to_list(length=None)
        
        user_ids = [u["user_id"] for u in users if "user_id" in u]
        
        if not user_ids:
            print(f"課程 {course_id} 目前沒有綁定的學生，略過推播公告")
            return

        text = f"🔔 【課堂公告】\n\n📌 標題：{announcement_data.get('title')}\n\n📝 內容：\n{announcement_data.get('content')}"
        
        batch_size = 500
        try:
            async with AsyncApiClient(self.configuration) as api_client:
                line_bot_api = AsyncMessagingApi(api_client)
                
                for i in range(0, len(user_ids), batch_size):
                    batch_user_ids = user_ids[i:i+batch_size]
                    await line_bot_api.multicast(
                        MulticastRequest(
                            to=batch_user_ids,
                            messages=[TextMessage(text=text)]
                        )
                    )
            print(f"✅ 成功推播公告給 {len(user_ids)} 位學生")
        except Exception as e:
            print(f"❌ 推播公告失敗: {str(e)}")
            traceback.print_exc()

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
        """處理按鈕回傳事件"""
        pass

    async def handle_text_message(self, event: MessageEvent):
        """處理文字訊息的主邏輯"""
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        reply_token = event.reply_token
        
        database = db.get_db()

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

        if message_text.startswith("綁定 "):
            await self._handle_bind_course(user_id, message_text, reply_token)
            return
            
        if message_text == "解除綁定":
            await self._handle_unbind_course(user_id, reply_token)
            return

        await self._handle_question(user_id, pseudonym, message_text, reply_token, event.message.id)

    async def _handle_bind_course(self, user_id: str, message_text: str, reply_token: str):
        """處理綁定課程邏輯"""
        database = db.get_db()
        parts = message_text.split(" ", 1)
        if len(parts) < 2:
            await self._reply_text(reply_token, "⚠️ 格式錯誤。請輸入「綁定 [課程代碼]」。")
            return
            
        course_code = parts[1].strip()
        course = None
        try:
            course = await database["courses"].find_one({"_id": ObjectId(course_code)})
        except:
            course = await database["courses"].find_one({"course_name": course_code})
            
        if not course:
            await self._reply_text(reply_token, f"❌ 找不到代碼為「{course_code}」的課程。請向助教或老師確認正確的代碼喔！")
            return

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

    async def _handle_question(self, user_id: str, pseudonym: str, message_text: str, reply_token: str, message_id: str):
        """處理學生提問與回覆邏輯 (僅限 Q&A 任務)"""
        database = db.get_db()
        
        user_data = await database["line_users"].find_one({"user_id": user_id})
        
        if not user_data or not user_data.get("current_course_id"):
            await self._reply_text(reply_token, "⚠️ 您尚未綁定任何課程！\n請先輸入「綁定 [課程代碼]」來告訴我您要參與哪堂課。")
            return

        course_id = user_data["current_course_id"]
        now = datetime.utcnow()
        
        # =========== 🔥 修改 2：將 $or 加入查詢，允許 expires_at 為 None (代表不限時) ===========
        active_qa = await database["qas"].find_one({
            "course_id": course_id,
            "allow_replies": True,
            "$or": [
                {"expires_at": None},
                {"expires_at": {"$gt": now}}
            ]
        }, sort=[("created_at", -1)])
        # ==============================================================================
        
        if not active_qa:
            await self._reply_text(reply_token, "ℹ️ 目前沒有開放中的課後 Q&A 任務喔！\n請等候老師或助教發布本週的問題後，再直接於此回覆您的答案。")
            return
            
        reply_to_qa_id = str(active_qa["_id"])
        
        # 防重複作答檢查邏輯
        existing_reply = await database["questions"].find_one({
            "reply_to_qa_id": reply_to_qa_id,
            "pseudonym": pseudonym 
        })
        
        if existing_reply:
            await self._reply_text(reply_token, "⚠️ 您已經提交過這題的答案囉！請耐心等候老師批閱。")
            return

        # 寫入資料庫
        try:
            new_q_data = QuestionCreate(
                course_id=course_id,
                line_user_id=user_id,
                question_text=message_text,
                original_message_id=message_id,
                reply_to_qa_id=reply_to_qa_id 
            )
            
            await question_service.create_question(new_q_data)
            await self._reply_text(reply_token, "✅ 已成功收到您的作答！")
            
        except ValueError as ve:
            await self._reply_text(reply_token, f"❌ 操作失敗：{str(ve)}")
        except Exception as e:
            print(f"❌ 寫入失敗: {str(e)}")
            traceback.print_exc()
            await self._reply_text(reply_token, "❌ 系統發生小錯誤，請稍後再試一次。")

line_service = LineService()