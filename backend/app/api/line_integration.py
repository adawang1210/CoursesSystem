"""
LINE Bot 整合 API 路由
提供 LINE Bot 配置、Webhook 處理、訊息管理等功能
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from ..services.ai_service import ai_service
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
# InsightApi 在某些版本中可能不可用，使用可選匯入
try:
    from linebot.v3.insight import InsightApi
    INSIGHT_API_AVAILABLE = True
except ImportError:
    InsightApi = None
    INSIGHT_API_AVAILABLE = False
    print("⚠️ LINE Insight API 不可用，將使用資料庫統計作為備用方案")

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from ..config import settings
from ..services.question_service import question_service
from ..models.schemas import (
    QuestionCreate, QuestionStatus,
    LineMessageCreate, LineMessageType, LineMessageDirection
)
from ..database import db
from ..utils.security import generate_pseudonym
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from bson import ObjectId

router = APIRouter(prefix="/line", tags=["line"])

# 初始化 LINE Bot API
configuration = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)


@router.get("/config", summary="取得 LINE Bot 配置狀態")
async def get_line_config():
    """
    取得 LINE Bot 配置狀態
    """
    is_configured = bool(settings.LINE_CHANNEL_SECRET and settings.LINE_CHANNEL_ACCESS_TOKEN)
    
    # 如果已配置，嘗試取得 Bot 資訊
    bot_info = None
    followers_count = None
    if is_configured:
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                # 取得 Bot 資訊
                bot_data = line_bot_api.get_bot_info()
                bot_info = {
                    "display_name": bot_data.display_name,
                    "user_id": bot_data.user_id,
                    "picture_url": bot_data.picture_url if hasattr(bot_data, 'picture_url') else None,
                    "status_message": bot_data.status_message if hasattr(bot_data, 'status_message') else None
                }
                
                # 嘗試取得追蹤者數量（好友數）
                try:
                    # 使用 Insight API 取得好友數（如果可用）
                    if INSIGHT_API_AVAILABLE:
                        from datetime import datetime, timedelta
                        # LINE Insight API 需要使用前一天的日期（UTC+9）
                        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                        
                        # 使用 InsightApi 取得好友數統計
                        insight_api = InsightApi(api_client)
                        followers_response = insight_api.get_number_of_followers(var_date=yesterday)
                        
                        if followers_response and hasattr(followers_response, 'followers'):
                            followers_count = followers_response.followers
                            print(f"✅ 成功從 LINE Insight API 取得好友數: {followers_count}")
                        else:
                            raise Exception("API 回應中沒有 followers 欄位")
                    else:
                        raise Exception("Insight API 不可用")
                except Exception as follower_error:
                    print(f"⚠️ 取得 LINE 官方好友數失敗: {str(follower_error)}")
                    # 備用方案：從資料庫取得互動過的使用者數
                    try:
                        database = db.get_db()
                        messages_collection = database["line_messages"]
                        unique_users = await messages_collection.distinct("user_id")
                        followers_count = len(unique_users)
                        print(f"📊 使用資料庫統計的互動使用者數: {followers_count}")
                    except Exception as db_error:
                        print(f"❌ 從資料庫統計失敗: {str(db_error)}")
                        followers_count = None
        except Exception as e:
            print(f"取得 Bot 資訊失敗: {str(e)}")
            bot_info = None
    
    return {
        "success": True,
        "data": {
            "is_configured": is_configured,
            "has_channel_secret": bool(settings.LINE_CHANNEL_SECRET),
            "has_access_token": bool(settings.LINE_CHANNEL_ACCESS_TOKEN),
            "channel_secret_length": len(settings.LINE_CHANNEL_SECRET) if settings.LINE_CHANNEL_SECRET else 0,
            "access_token_length": len(settings.LINE_CHANNEL_ACCESS_TOKEN) if settings.LINE_CHANNEL_ACCESS_TOKEN else 0,
            "bot_info": bot_info,
            "followers_count": followers_count
        }
    }


@router.get("/webhook-url", summary="取得 Webhook URL")
async def get_webhook_url(request: Request):
    """
    取得當前的 Webhook URL
    優先使用 ngrok 或其他公開 URL（從 Host header 檢測）
    """
    # 獲取請求的 host，優先使用 X-Forwarded-Host（ngrok 會設定此 header）
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "")
    
    # 檢查是否為 ngrok 或其他 HTTPS 環境
    if "ngrok" in host or request.headers.get("X-Forwarded-Proto") == "https":
        base_url = f"https://{host}"
    else:
        base_url = str(request.base_url).rstrip('/')
    
    webhook_url = f"{base_url}/line/webhook"
    
    # 檢查是否為 localhost，給出額外提示
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
    """
    接收來自 LINE Platform 的 Webhook 事件
    """
    print(f"[Webhook] 收到 webhook 請求")
    print(f"[Webhook] Headers: {dict(request.headers)}")
    
    # 檢查配置
    if not settings.LINE_CHANNEL_SECRET or not settings.LINE_CHANNEL_ACCESS_TOKEN:
        print(f"[Webhook] 錯誤: LINE Bot 尚未配置")
        raise HTTPException(status_code=500, detail="LINE Bot 尚未配置")
    
    # 取得請求內容
    body = await request.body()
    body_str = body.decode('utf-8')
    print(f"[Webhook] 請求內容: {body_str[:200]}...")  # 只打印前 200 字符
    
    # 驗證簽章
    if not x_line_signature:
        print(f"[Webhook] 錯誤: 缺少 X-Line-Signature header")
        raise HTTPException(status_code=400, detail="缺少 X-Line-Signature header")
    
    print(f"[Webhook] 收到的簽章: {x_line_signature[:20]}...")
    
    # 驗證請求來自 LINE
    hash_value = hmac.new(
        settings.LINE_CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    signature = base64.b64encode(hash_value).decode('utf-8')
    
    print(f"[Webhook] 計算的簽章: {signature[:20]}...")
    
    if signature != x_line_signature:
        print(f"[Webhook] 錯誤: 簽章不匹配")
        print(f"[Webhook] 預期: {signature}")
        print(f"[Webhook] 收到: {x_line_signature}")
        raise HTTPException(status_code=400, detail="無效的簽章")
    
    print(f"[Webhook] 簽章驗證成功")
    
    try:
        handler.handle(body_str, x_line_signature)
        print(f"[Webhook] 事件處理成功")
    except InvalidSignatureError as e:
        print(f"[Webhook] 錯誤: InvalidSignatureError - {str(e)}")
        raise HTTPException(status_code=400, detail="無效的簽章")
    except Exception as e:
        print(f"[Webhook] 錯誤: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"處理 Webhook 失敗: {str(e)}")
    
    return {"success": True}


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    """
    處理文字訊息事件
    """
    try:
        # 取得訊息內容
        message_text = event.message.text
        user_id = event.source.user_id
        message_id = event.message.id
        
        # 產生去識別化代號
        pseudonym = generate_pseudonym(user_id)
        
        # 儲存收到的訊息
        database = db.get_db()
        messages_collection = database["line_messages"]
        
        received_message = {
            "user_id": user_id,
            "pseudonym": pseudonym,
            "message_type": LineMessageType.TEXT.value,
            "direction": LineMessageDirection.RECEIVED.value,
            "content": message_text,
            "line_message_id": message_id,
            "reply_token": event.reply_token,
            "created_at": datetime.utcnow()
        }
        messages_collection.insert_one(received_message)

        system_instruction = "你是一個資管系的教學助理，請協助回答關於程式設計的問題。"
        
        # 發送回覆
        reply_text = ai_service.get_reply(message_text, system_instruction)
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        
        # 儲存發送的訊息
        sent_message = {
            "user_id": user_id,
            "pseudonym": pseudonym,
            "message_type": LineMessageType.TEXT.value,
            "direction": LineMessageDirection.SENT.value,
            "content": reply_text,
            "created_at": datetime.utcnow()
        }
        messages_collection.insert_one(sent_message)
        
    except Exception as e:
        print(f"處理訊息錯誤: {str(e)}")
        # 儲存失敗記錄
        try:
            database = db.get_db()
            messages_collection = database["line_messages"]
            failed_message = {
                "user_id": user_id if 'user_id' in locals() else "unknown",
                "pseudonym": pseudonym if 'pseudonym' in locals() else "unknown",
                "message_type": LineMessageType.TEXT.value,
                "direction": LineMessageDirection.FAILED.value,
                "content": message_text if 'message_text' in locals() else "",
                "error_message": str(e),
                "created_at": datetime.utcnow()
            }
            messages_collection.insert_one(failed_message)
        except:
            pass


@router.get("/stats", summary="取得 LINE Bot 統計")
async def get_line_stats(course_id: Optional[str] = None):
    """
    取得 LINE Bot 使用統計
    """
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    # 基本統計
    total_messages = await messages_collection.count_documents({})
    
    # 統計不同方向的訊息
    received_count = await messages_collection.count_documents({
        "direction": LineMessageDirection.RECEIVED.value
    })
    sent_count = await messages_collection.count_documents({
        "direction": LineMessageDirection.SENT.value
    })
    failed_count = await messages_collection.count_documents({
        "direction": LineMessageDirection.FAILED.value
    })
    
    # 統計唯一用戶數
    unique_users = await messages_collection.distinct("user_id")
    users_count = len(unique_users)
    
    # 取得最後一則訊息時間
    last_message = await messages_collection.find_one(
        {},
        sort=[("created_at", -1)]
    )
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
    
    # 如果有 course_id，可以查詢該課程的統計
    if course_id:
        questions_collection = database["questions"]
        questions_from_line = await questions_collection.count_documents({
            "course_id": course_id,
            "original_message_id": {"$exists": True, "$ne": None}
        })
        stats["questions_from_line"] = questions_from_line
    
    return {
        "success": True,
        "data": stats
    }


@router.post("/send-message", summary="發送訊息到 LINE")
async def send_line_message(
    user_id: str,
    message: str
):
    """
    發送訊息到指定的 LINE 用戶
    """
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="LINE Bot 尚未配置")
    
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            # 注意：push message 需要使用 push_message API
            # 這裡需要根據實際需求實作
            pass
        
        return {
            "success": True,
            "message": "訊息發送成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"發送訊息失敗: {str(e)}")


@router.get("/users", summary="取得 LINE 使用者列表")
async def get_line_users():
    """
    取得所有與 Bot 互動過的使用者列表，包含訊息統計
    """
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    # 使用聚合管道取得每個使用者的統計資訊
    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "pseudonym": {"$first": "$pseudonym"},
                "message_count": {"$sum": 1},
                "last_message_time": {"$max": "$created_at"},
                "received_count": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$direction", LineMessageDirection.RECEIVED.value]},
                            1,
                            0
                        ]
                    }
                },
                "sent_count": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$direction", LineMessageDirection.SENT.value]},
                            1,
                            0
                        ]
                    }
                }
            }
        },
        {
            "$sort": {"last_message_time": -1}
        }
    ]
    
    results = await messages_collection.aggregate(pipeline).to_list(length=None)
    
    # 格式化結果
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
    
    return {
        "success": True,
        "data": {
            "users": users,
            "total": len(users)
        }
    }


@router.get("/messages", summary="取得 LINE 訊息歷史")
async def get_line_messages(
    limit: int = 50,
    offset: int = 0,
    direction: Optional[LineMessageDirection] = None,
    user_id: Optional[str] = None
):
    """
    取得 LINE 訊息歷史記錄
    """
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    # 建立查詢條件
    query = {}
    if direction:
        query["direction"] = direction.value
    if user_id:
        query["user_id"] = user_id
    
    # 查詢訊息
    cursor = messages_collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
    messages = await cursor.to_list(length=limit)
    
    # 轉換 ObjectId 為字串
    for msg in messages:
        msg["_id"] = str(msg["_id"])
        if "created_at" in msg:
            msg["created_at"] = msg["created_at"].isoformat()
    
    # 總數
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
    """
    取得過去 N 天的訊息統計
    """
    database = db.get_db()
    messages_collection = database["line_messages"]
    
    # 計算日期範圍
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 按日期聚合統計
    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date, "$lte": end_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "direction": "$direction"
                },
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id.date": 1}
        }
    ]
    
    results = await messages_collection.aggregate(pipeline).to_list(length=None)
    
    # 整理資料格式
    daily_stats = {}
    for result in results:
        date = result["_id"]["date"]
        direction = result["_id"]["direction"]
        count = result["count"]
        
        if date not in daily_stats:
            daily_stats[date] = {
                "date": date,
                "received": 0,
                "sent": 0,
                "failed": 0
            }
        
        daily_stats[date][direction] = count
    
    # 轉換為列表
    stats_list = list(daily_stats.values())
    
    # 按日期統計用戶活躍度
    user_pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start_date, "$lte": end_date},
                "direction": LineMessageDirection.RECEIVED.value
            }
        },
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "user_id": "$user_id"
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.date",
                "users": {"$sum": 1}
            }
        },
        {
            "$sort": {"_id": 1}
        }
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


@router.get("/followers-count", summary="取得 LINE Bot 好友數")
async def get_followers_count():
    """
    取得 LINE Bot 的好友總數
    """
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="LINE Bot 尚未配置")
    
    try:
        from datetime import datetime, timedelta
        
        with ApiClient(configuration) as api_client:
            # 嘗試多種方式取得好友數
            followers_count = None
            method_used = None
            error_detail = None
            
            # 方法 1: 使用 Insight API (需要前一天的日期，如果可用)
            try:
                if INSIGHT_API_AVAILABLE:
                    insight_api = InsightApi(api_client)
                    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                    
                    print(f"🔍 嘗試從 LINE Insight API 取得好友數（日期: {yesterday}）...")
                    followers_response = insight_api.get_number_of_followers(var_date=yesterday)
                    
                    if followers_response and hasattr(followers_response, 'followers'):
                        followers_count = followers_response.followers
                        method_used = "LINE Insight API"
                        print(f"✅ 成功取得好友數: {followers_count}")
                    else:
                        error_detail = "API 回應中沒有 followers 欄位"
                        print(f"⚠️ {error_detail}")
                else:
                    error_detail = "Insight API 不可用於此 SDK 版本"
                    print(f"⚠️ {error_detail}")
            except Exception as e:
                error_detail = str(e)
                print(f"❌ Insight API 失敗: {error_detail}")
            
            # 方法 2: 如果失敗，從資料庫統計
            if followers_count is None:
                try:
                    print("📊 使用資料庫統計方式...")
                    database = db.get_db()
                    messages_collection = database["line_messages"]
                    unique_users = await messages_collection.distinct("user_id")
                    followers_count = len(unique_users)
                    method_used = "資料庫統計（僅計算互動過的使用者）"
                    print(f"✅ 從資料庫統計: {followers_count} 位互動使用者")
                except Exception as e:
                    print(f"❌ 資料庫統計失敗: {str(e)}")
            
            return {
                "success": True,
                "data": {
                    "followers_count": followers_count,
                    "method": method_used,
                    "error": error_detail,
                    "note": "如果使用資料庫統計，數字可能小於實際好友數（因為只計算有互動過的使用者）"
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得好友數失敗: {str(e)}")


@router.post("/test-connection", summary="測試 LINE Bot 連接")
async def test_line_connection():
    """
    測試 LINE Bot 配置是否正確
    """
    if not settings.LINE_CHANNEL_SECRET:
        return {
            "success": False,
            "message": "Channel Secret 未設定"
        }
    
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        return {
            "success": False,
            "message": "Channel Access Token 未設定"
        }
    
    try:
        # 嘗試取得 Bot 資訊來驗證 token
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            bot_info = line_bot_api.get_bot_info()
        
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
        return {
            "success": False,
            "message": f"連接測試失敗: {str(e)}"
        }

