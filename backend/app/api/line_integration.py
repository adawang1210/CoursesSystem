"""
LINE Bot 整合 API 路由
提供 LINE Bot 配置、Webhook 處理、訊息管理等功能
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId

# 使用 WebhookParser 來支援 FastAPI 非同步架構
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    FollowEvent
)

try:
    from linebot.v3.insight import InsightApi
    INSIGHT_API_AVAILABLE = True
except ImportError:
    InsightApi = None
    INSIGHT_API_AVAILABLE = False

from ..config import settings
from ..database import db
from ..services.line_service import line_service

router = APIRouter(prefix="/line", tags=["line"])

# 初始化 LINE Bot API
configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


@router.get("/config", summary="取得 LINE Bot 配置狀態")
async def get_line_config():
    is_configured = bool(settings.LINE_CHANNEL_SECRET and settings.LINE_CHANNEL_ACCESS_TOKEN)
    bot_info = None
    followers_count = None
    
    if is_configured:
        try:
            # 🔥 修正：使用 AsyncApiClient 與 AsyncMessagingApi
            async with AsyncApiClient(configuration) as api_client:
                line_bot_api = AsyncMessagingApi(api_client)
                bot_data = await line_bot_api.get_bot_info()
                
                bot_info = {
                    "display_name": bot_data.display_name,
                    "user_id": bot_data.user_id,
                    "picture_url": getattr(bot_data, "picture_url", ""), # 使用 getattr 避免機器人沒大頭貼時報錯
                    "status_message": ""  # 機器人本身沒有狀態消息，直接給空字串
                }
                
                # 嘗試從資料庫取得統計好友數
                try:
                    database = db.get_db()
                    messages_collection = database["line_messages"]
                    unique_users = await messages_collection.distinct("user_id")
                    followers_count = len(unique_users)
                except Exception as db_error:
                    print(f"從資料庫統計失敗: {str(db_error)}")
        except Exception as e:
            print(f"取得 Bot 資訊失敗: {str(e)}")
            
    return {
        "success": True,
        "data": {
            "is_configured": is_configured,
            "bot_info": bot_info,
            "followers_count": followers_count
        }
    }


@router.get("/webhook-url", summary="取得 Webhook URL")
async def get_webhook_url(request: Request):
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "")
    
    if "ngrok" in host or request.headers.get("X-Forwarded-Proto") == "https":
        base_url = f"https://{host}"
    else:
        base_url = str(request.base_url).rstrip('/')
    
    webhook_url = f"{base_url}/line/webhook"
    
    is_local = "localhost" in webhook_url or "127.0.0.1" in webhook_url
    instructions = [
        "1. 前往 LINE Developers Console",
        "2. 選擇您的 Messaging API Channel",
        "3. 在 Messaging API 標籤中找到 Webhook settings",
        "4. 將上方的 Webhook URL 貼入",
        "5. 啟用 Use webhook",
        "6. 點擊 Verify 驗證連接"
    ]
    if is_local:
        instructions.insert(0, "⚠️  警告：LINE 需要 HTTPS URL，請使用 ngrok 或其他隧道服務")
        
    return {
        "success": True, 
        "data": {
            "webhook_url": webhook_url,
            "is_https": webhook_url.startswith("https://"),
            "instructions": instructions
        }
    }


@router.post("/webhook", summary="LINE Bot Webhook 接收器")
async def line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(None)
):
    if not settings.LINE_CHANNEL_SECRET or not settings.LINE_CHANNEL_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="LINE Bot 尚未配置")
    
    body = await request.body()
    body_str = body.decode('utf-8')
    
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="缺少 X-Line-Signature header")
    
    try:
        # 使用 parser 解析並派發給 LineService
        events = parser.parse(body_str, x_line_signature)
        
        print(f"📥 收到 LINE 事件，共 {len(events)} 筆")  # 🔥 探照燈 1
        
        for event in events:
            print(f"🔍 正在處理事件類型: {type(event)}")  # 🔥 探照燈 2
            
            if isinstance(event, MessageEvent):
                if isinstance(event.message, TextMessageContent):
                    print(f"💬 進入文字處理邏輯，內容: {event.message.text}")  # 🔥 探照燈 3
                    await line_service.handle_text_message(event)
            elif isinstance(event, PostbackEvent):
                await line_service.handle_postback(event)
            elif isinstance(event, FollowEvent):
                await line_service.handle_follow(event)
                
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="無效的簽章")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"處理 Webhook 失敗: {str(e)}")
    
    return {"success": True}


@router.get("/stats", summary="取得 LINE Bot 統計")
async def get_line_stats(course_id: Optional[str] = None):
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    total_messages = await messages_collection.count_documents({})
    received_count = await messages_collection.count_documents({"direction": "received"})
    sent_count = await messages_collection.count_documents({"direction": "sent"})
    failed_count = await messages_collection.count_documents({"direction": "failed"})
    
    unique_users = await messages_collection.distinct("user_id")
    users_count = len(unique_users)
    
    last_message = await messages_collection.find_one({}, sort=[("created_at", -1)])
    last_message_time = last_message["created_at"] if last_message else None
    
    stats = {
        "messages_count": total_messages,
        "received_count": received_count,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "users_count": users_count,
        "questions_from_line": 0,
        "last_message_time": last_message_time.isoformat() if last_message_time else None
    }
    
    if course_id:
        questions_collection = database["questions"]
        stats["questions_from_line"] = await questions_collection.count_documents({
            "course_id": course_id,
            "original_message_id": {"$exists": True, "$ne": None}
        })
    
    return {"success": True, "data": stats}


@router.get("/users", summary="取得 LINE 使用者列表")
async def get_line_users():
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "pseudonym": {"$first": "$pseudonym"},
                "message_count": {"$sum": 1},
                "last_message_time": {"$max": "$created_at"},
                "received_count": {
                    "$sum": {"$cond": [{"$eq": ["$direction", "received"]}, 1, 0]}
                },
                "sent_count": {
                    "$sum": {"$cond": [{"$eq": ["$direction", "sent"]}, 1, 0]}
                }
            }
        },
        {"$sort": {"last_message_time": -1}}
    ]
    
    results = await messages_collection.aggregate(pipeline).to_list(length=None)
    users = []
    for result in results:
        users.append({
            "user_id": result["_id"],
            "pseudonym": result["pseudonym"],
            "message_count": result["message_count"],
            "received_count": result["received_count"],
            "sent_count": result["sent_count"],
            "last_message_time": result["last_message_time"].isoformat() if result["last_message_time"] else None
        })
    
    return {"success": True, "data": {"users": users, "total": len(users)}}


@router.get("/messages", summary="取得 LINE 訊息歷史")
async def get_line_messages(
    limit: int = 50,
    offset: int = 0,
    direction: Optional[str] = None,
    user_id: Optional[str] = None
):
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    query = {}
    if direction:
        query["direction"] = direction
    if user_id:
        query["user_id"] = user_id
    
    cursor = messages_collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
    messages = await cursor.to_list(length=limit)
    
    for msg in messages:
        msg["_id"] = str(msg["_id"])
        if "created_at" in msg:
            msg["created_at"] = msg["created_at"].isoformat()
    
    total = await messages_collection.count_documents(query)
    
    return {
        "success": True,
        "data": {
            "messages": messages,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/message-stats", summary="取得訊息統計資料")
async def get_message_stats(days: int = 7):
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "direction": "$direction"
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id.date": 1}}
    ]
    
    results = await messages_collection.aggregate(pipeline).to_list(length=None)
    daily_stats = {}
    for result in results:
        date = result["_id"]["date"]
        direction = result["_id"]["direction"]
        count = result["count"]
        if date not in daily_stats:
            daily_stats[date] = {"date": date, "received": 0, "sent": 0, "failed": 0}
        daily_stats[date][direction] = count
        
    stats_list = list(daily_stats.values())
    
    user_pipeline = [
        {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}, "direction": "received"}},
        {"$group": {"_id": {"date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "user_id": "$user_id"}}},
        {"$group": {"_id": "$_id.date", "users": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    
    user_results = await messages_collection.aggregate(user_pipeline).to_list(length=None)
    user_stats = {result["_id"]: result["users"] for result in user_results}
    
    return {
        "success": True,
        "data": {
            "daily_message_stats": stats_list,
            "daily_user_stats": user_stats
        }
    }


@router.post("/test-connection", summary="測試 LINE Bot 連接")
async def test_line_connection():
    if not settings.LINE_CHANNEL_SECRET or not settings.LINE_CHANNEL_ACCESS_TOKEN:
        return {"success": False, "message": "尚未配置 Channel Secret 或 Access Token"}
    
    try:
        # 🔥 修正：使用 AsyncApiClient 與 AsyncMessagingApi
        async with AsyncApiClient(configuration) as api_client:
            line_bot_api = AsyncMessagingApi(api_client)
            bot_info = await line_bot_api.get_bot_info()
        
        return {
            "success": True,
            "message": "LINE Bot 連接正常",
            "data": {
                "bot_name": bot_info.display_name if bot_info else None,
                "channel_secret": f"{settings.LINE_CHANNEL_SECRET[:8]}..." if len(settings.LINE_CHANNEL_SECRET) > 8 else "***",
                "access_token": f"{settings.LINE_CHANNEL_ACCESS_TOKEN[:20]}..." if len(settings.LINE_CHANNEL_ACCESS_TOKEN) > 20 else "***"
            }
        }
    except Exception as e:
        return {"success": False, "message": f"連接測試失敗: {str(e)}"}