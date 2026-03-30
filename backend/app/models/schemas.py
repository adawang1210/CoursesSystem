"""
資料庫 Schema 定義
定義所有核心資料模型的結構
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚舉類型 ====================

class ReviewStatus(str, Enum):
    """作答批閱狀態"""
    PENDING = "pending"    # 待批閱
    APPROVED = "approved"  # 通過 / 觀念正確
    REJECTED = "rejected"  # 退回 / 觀念錯誤或需補充


class UserRole(str, Enum):
    """使用者角色"""
    TEACHER = "teacher"  # 教師
    ASSISTANT = "assistant"  # 助教
    STUDENT = "student"  # 學生


class DifficultyLevel(str, Enum):
    """問題難度"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ==================== 基礎模型 ====================

class PyObjectId(str):
    """MongoDB ObjectId 的 Pydantic 類型"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        from bson import ObjectId
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


# ==================== 課程相關模型 ====================

class CourseBase(BaseModel):
    """課程基礎模型"""
    course_code: str = Field(..., description="課程代碼")
    course_name: str = Field(..., description="課程名稱")
    semester: str = Field(..., description="學期 (例: 113-1)")
    description: Optional[str] = Field(None, description="課程描述")
    teacher_ids: List[str] = Field(default_factory=list, description="授課教師ID列表")
    is_active: bool = Field(default=True, description="是否啟用")


class CourseCreate(CourseBase):
    """建立課程"""
    pass


class Course(CourseBase):
    """課程完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== 班級相關模型 ====================

class ClassBase(BaseModel):
    """班級基礎模型"""
    course_id: str = Field(..., description="所屬課程ID")
    class_code: str = Field(..., description="班級代碼")
    class_name: str = Field(..., description="班級名稱")
    assistant_ids: List[str] = Field(default_factory=list, description="助教ID列表")
    line_group_id: Optional[str] = Field(None, description="Line 群組ID")
    is_active: bool = Field(default=True, description="是否啟用")


class ClassCreate(ClassBase):
    """建立班級"""
    pass


class Class(ClassBase):
    """班級完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== 提問/作答紀錄相關模型 ====================

class QuestionBase(BaseModel):
    """作答紀錄基礎模型"""
    course_id: str = Field(..., description="所屬課程ID")
    class_id: Optional[str] = Field(None, description="所屬班級ID")
    pseudonym: str = Field(..., description="去識別化後的使用者代號")
    
    # =========== 🔥 新增：學號欄位 ===========
    student_id: Optional[str] = Field(None, description="學生學號")
    # =======================================
    
    question_text: str = Field(..., description="作答內容")
    
    review_status: ReviewStatus = Field(default=ReviewStatus.PENDING, description="批閱狀態")
    feedback: Optional[str] = Field(None, description="老師給予的批閱評語")
    
    # AI 分析結果
    cluster_id: Optional[str] = Field(None, description="AI 聚類ID")
    difficulty_score: Optional[float] = Field(None, description="難度分數 (0-1)")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="難度等級")
    keywords: List[str] = Field(default_factory=list, description="關鍵字列表")

    ai_response_draft: Optional[str] = Field(None, description="AI 生成的回覆草稿")
    ai_summary: Optional[str] = Field(None, description="AI 對問題的摘要或重述")
    sentiment_score: Optional[float] = Field(None, description="情緒分數 (-1 to 1)")
    
    # 關聯 Q&A 任務
    reply_to_qa_id: Optional[str] = Field(None, description="回覆特定 Q&A 的 ID")
    
    # 元資料
    original_message_id: Optional[str] = Field(None, description="Line 訊息ID")
    source: str = Field(default="WEB", description="提問來源 (WEB, LINE)")


class QuestionCreate(BaseModel):
    """建立作答 (接收 Line Bot 輸入)"""
    course_id: str
    class_id: Optional[str] = None
    line_user_id: str = Field(..., description="Line User ID (將被去識別化)")
    
    # 🔥 新增傳遞學號
    student_id: Optional[str] = None
    
    question_text: str
    original_message_id: Optional[str] = None
    reply_to_qa_id: Optional[str] = None


class ReviewStatusUpdate(BaseModel):
    """更新單筆批閱狀態與評語"""
    review_status: ReviewStatus = Field(..., description="新批閱狀態")
    feedback: Optional[str] = Field(None, description="給學生的批閱評語(可選)")


class ReviewStatusBatchUpdate(BaseModel):
    """批量更新多筆作答的批閱狀態"""
    question_ids: List[str] = Field(..., description="待更新的作答紀錄ID列表")
    review_status: ReviewStatus = Field(..., description="新批閱狀態")
    feedback: Optional[str] = Field(None, description="給這些學生的統一批閱評語(可選)")


class Question(QuestionBase):
    """作答紀錄完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== Q&A 相關模型 ====================

class QABase(BaseModel):
    """Q&A 任務基礎模型"""
    course_id: str = Field(..., description="所屬課程ID")
    class_id: Optional[str] = Field(None, description="所屬班級ID (可為 None 代表全課程)")
    question: str = Field(..., description="問題內容")
    
    core_concept: str = Field(..., description="期望的核心觀念")
    expected_misconceptions: Optional[str] = Field(None, description="預期的迷思概念或分析重點")
    
    category: Optional[str] = Field(None, description="分類")
    tags: List[str] = Field(default_factory=list, description="標籤")
    
    is_published: bool = Field(default=False, description="是否發布")
    publish_date: Optional[datetime] = Field(None, description="發布時間")
    
    created_by: str = Field(..., description="建立者ID (教師/助教)")

    allow_replies: bool = Field(default=False, description="是否透過 LINE 開放學生限時回覆")
    duration_minutes: Optional[int] = Field(None, description="開放回覆的時長(分鐘)")
    expires_at: Optional[datetime] = Field(None, description="限時回覆截止時間")
    
    max_attempts: Optional[int] = Field(default=1, description="每位學生最大作答次數")


class QACreate(BaseModel):
    """建立 Q&A"""
    course_id: str
    class_id: Optional[str] = None
    question: str
    
    core_concept: str
    expected_misconceptions: Optional[str] = None
    
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_published: bool = False
    
    allow_replies: bool = False
    duration_minutes: Optional[int] = None
    max_attempts: Optional[int] = 1
    created_by: str = Field("system", description="建立者ID")


class QA(QABase):
    """Q&A 完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== 公告相關模型 ====================

class AnnouncementBase(BaseModel):
    """公告基礎模型"""
    course_id: str = Field(..., description="所屬課程ID")
    class_id: Optional[str] = Field(None, description="所屬班級ID (可為 None 代表全課程)")
    title: str = Field(..., description="公告標題")
    content: str = Field(..., description="公告內容")
    
    related_qa_ids: List[str] = Field(default_factory=list, description="相關 Q&A ID列表")
    
    is_published: bool = Field(default=False, description="是否發布")
    publish_date: Optional[datetime] = Field(None, description="發布時間")
    
    sent_to_line: bool = Field(default=False, description="是否已發送至 Line")
    line_message_id: Optional[str] = Field(None, description="Line 訊息ID")
    
    created_by: str = Field(..., description="建立者ID (教師/助教)")


class AnnouncementCreate(BaseModel):
    """建立公告"""
    course_id: str
    class_id: Optional[str] = None
    title: str
    content: str
    related_qa_ids: List[str] = Field(default_factory=list)
    is_published: bool = False


class Announcement(AnnouncementBase):
    """公告完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== 使用者相關模型 ====================

class UserBase(BaseModel):
    """使用者基礎模型"""
    email: EmailStr = Field(..., description="電子郵件")
    name: str = Field(..., description="姓名")
    role: UserRole = Field(..., description="角色")
    is_active: bool = Field(default=True, description="是否啟用")


class UserCreate(UserBase):
    """建立使用者"""
    password: str = Field(..., description="密碼")


class User(UserBase):
    """使用者完整模型"""
    id: str = Field(alias="_id")
    hashed_password: str = Field(..., description="加密後的密碼")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== AI 分析相關模型 ====================

class AIAnalysisRequest(BaseModel):
    """AI 分析請求"""
    question_ids: List[str] = Field(..., description="待分析的提問ID列表")
    course_id: str = Field(..., description="課程ID")


class AIAnalysisResult(BaseModel):
    """AI 分析結果"""
    question_id: str = Field(..., description="提問ID")
    cluster_id: Optional[str] = Field(None, description="聚類ID")
    difficulty_score: float = Field(..., description="難度分數")
    keywords: List[str] = Field(default_factory=list, description="關鍵字")
    response_draft: Optional[str] = Field(None, description="AI 生成的回覆草稿")
    summary: Optional[str] = Field(None, description="問題摘要")
    suggested_tags: List[str] = Field(default_factory=list, description="建議標籤")
    sentiment_score: Optional[float] = Field(None, description="情緒分數")


# ==================== LINE 訊息相關模型 ====================

class LineMessageType(str, Enum):
    """LINE 訊息類型"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    LOCATION = "location"
    STICKER = "sticker"


class LineMessageDirection(str, Enum):
    """LINE 訊息方向"""
    RECEIVED = "received"
    SENT = "sent"
    FAILED = "failed"


class LineMessageBase(BaseModel):
    """LINE 訊息基礎模型"""
    user_id: str = Field(..., description="LINE 使用者 ID")
    pseudonym: str = Field(..., description="去識別化後的使用者代號")
    
    # =========== 🔥 新增：學號欄位 ===========
    student_id: Optional[str] = Field(None, description="學生學號")
    # =======================================
    
    message_type: LineMessageType = Field(..., description="訊息類型")
    direction: LineMessageDirection = Field(..., description="訊息方向")
    content: str = Field(..., description="訊息內容")
    
    course_id: Optional[str] = Field(None, description="關聯的課程ID")
    class_id: Optional[str] = Field(None, description="關聯的班級ID")
    question_id: Optional[str] = Field(None, description="關聯的提問ID")
    
    line_message_id: Optional[str] = Field(None, description="LINE 訊息ID")
    reply_token: Optional[str] = Field(None, description="回覆 token")
    
    error_message: Optional[str] = Field(None, description="錯誤訊息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他元資料")


class LineMessageCreate(BaseModel):
    """建立 LINE 訊息記錄"""
    user_id: str
    
    # 🔥 新增傳遞學號
    student_id: Optional[str] = None
    
    message_type: LineMessageType = LineMessageType.TEXT
    direction: LineMessageDirection
    content: str
    course_id: Optional[str] = None
    class_id: Optional[str] = None
    question_id: Optional[str] = None
    line_message_id: Optional[str] = None
    reply_token: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LineMessage(LineMessageBase):
    """LINE 訊息完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True

# ==================== 聚類 (Cluster) 相關模型 ====================

class ClusterBase(BaseModel):
    """AI 聚類主題模型"""
    course_id: str = Field(..., description="所屬課程ID")
    qa_id: Optional[str] = Field(None, description="關聯的 Q&A 題目 ID，代表此群組是針對該題目的回答分類")
    
    topic_label: str = Field(..., description="AI 生成的主題標籤 (例如：觀念完全正確、混淆某觀念)")
    summary: Optional[str] = Field(None, description="該主題的綜合摘要或批閱總結")
    keywords: List[str] = Field(default_factory=list, description="代表性關鍵字")
    
    question_count: int = Field(default=0, description="包含的問題/回答數量")
    avg_difficulty: float = Field(default=0.0, description="平均難度")

    is_locked: bool = Field(default=False, description="是否已被人工鎖定")
    manual_label: Optional[str] = Field(None, description="人工手動設定的標籤名稱")

class ClusterCreate(ClusterBase):
    pass

class Cluster(ClusterBase):
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True

class ClusterUpdate(BaseModel):
    topic_label: Optional[str] = Field(None, description="新的主題名稱")
    is_locked: bool = Field(default=True, description="更新後是否自動鎖定")

class ClusterGenerateRequest(BaseModel):
    course_id: str = Field(..., description="課程ID")
    qa_id: Optional[str] = Field(None, description="指定要進行聚類的 Q&A 題目 ID")
    max_clusters: int = Field(default=5, ge=1, le=20, description="群組數量上限")
    force_recluster: bool = Field(default=False, description="是否強制重新聚類 (將清除舊群組並重設作答標籤)")