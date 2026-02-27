"""
資料庫 Schema 定義
定義所有核心資料模型的結構
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚舉類型 ====================

class QuestionStatus(str, Enum):
    """提問狀態"""
    PENDING = "PENDING"  # 待處理
    APPROVED = "APPROVED"  # 已同意
    REJECTED = "REJECTED"  # 已拒絕
    DELETED = "DELETED"  # 已刪除
    WITHDRAWN = "WITHDRAWN"  # 已撤回


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
        json_schema_extra = {
            "example": {
                "course_code": "CS101",
                "course_name": "計算機概論",
                "semester": "113-1",
                "description": "計算機科學入門課程",
                "teacher_ids": ["teacher001"],
                "is_active": True
            }
        }


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


# ==================== 提問相關模型 ====================

class QuestionBase(BaseModel):
    """提問基礎模型"""
    course_id: str = Field(..., description="所屬課程ID")
    class_id: Optional[str] = Field(None, description="所屬班級ID")
    pseudonym: str = Field(..., description="去識別化後的使用者代號")
    question_text: str = Field(..., description="提問內容")
    status: QuestionStatus = Field(default=QuestionStatus.PENDING, description="提問狀態")
    
    # AI 分析結果
    cluster_id: Optional[str] = Field(None, description="AI 聚類ID")
    difficulty_score: Optional[float] = Field(None, description="難度分數 (0-1)")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="難度等級")
    keywords: List[str] = Field(default_factory=list, description="關鍵字列表")

    ai_response_draft: Optional[str] = Field(None, description="AI 生成的回覆草稿")
    ai_summary: Optional[str] = Field(None, description="AI 對問題的摘要或重述")
    sentiment_score: Optional[float] = Field(None, description="情緒分數 (-1 to 1)")
    
    # 合併相關
    merged_to_qa_id: Optional[str] = Field(None, description="合併至的 Q&A ID")
    is_merged: bool = Field(default=False, description="是否已合併")
    
    # 元資料
    original_message_id: Optional[str] = Field(None, description="Line 訊息ID")
    # 🔥 新增：來源標記 (預設 WEB)
    source: str = Field(default="WEB", description="提問來源 (WEB, LINE)")


class QuestionCreate(BaseModel):
    """建立提問 (接收 Line Bot 輸入)"""
    course_id: str
    class_id: Optional[str] = None
    line_user_id: str = Field(..., description="Line User ID (將被去識別化)")
    question_text: str
    original_message_id: Optional[str] = None


class QuestionStatusUpdate(BaseModel):
    """更新提問狀態"""
    status: QuestionStatus = Field(..., description="新狀態")
    rejection_reason: Optional[str] = Field(None, description="拒絕原因（狀態為 REJECTED 時使用）")


class Question(QuestionBase):
    """提問完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


# ==================== Q&A 相關模型 ====================

class QABase(BaseModel):
    """Q&A 基礎模型"""
    course_id: str = Field(..., description="所屬課程ID")
    class_id: Optional[str] = Field(None, description="所屬班級ID (可為 None 代表全課程)")
    question: str = Field(..., description="問題內容")
    answer: str = Field(..., description="回答內容")
    
    # 相關提問
    related_question_ids: List[str] = Field(default_factory=list, description="相關提問ID列表")
    
    # 分類與標籤
    category: Optional[str] = Field(None, description="分類")
    tags: List[str] = Field(default_factory=list, description="標籤")
    
    # 顯示控制
    is_published: bool = Field(default=False, description="是否發布")
    publish_date: Optional[datetime] = Field(None, description="發布時間")
    
    # 作者資訊
    created_by: str = Field(..., description="建立者ID (教師/助教)")


class QACreate(BaseModel):
    """建立 Q&A"""
    course_id: str
    class_id: Optional[str] = None
    question: str
    answer: str
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_published: bool = False


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
    
    # 關聯的 Q&A
    related_qa_ids: List[str] = Field(default_factory=list, description="相關 Q&A ID列表")
    
    # 發布控制
    is_published: bool = Field(default=False, description="是否發布")
    publish_date: Optional[datetime] = Field(None, description="發布時間")
    
    # 發送至 Line
    sent_to_line: bool = Field(default=False, description="是否已發送至 Line")
    line_message_id: Optional[str] = Field(None, description="Line 訊息ID")
    
    # 作者資訊
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
    # 🔥 修改：cluster_id 改為 Optional，因新提問尚未分群
    cluster_id: Optional[str] = Field(None, description="聚類ID")
    difficulty_score: float = Field(..., description="難度分數")
    keywords: List[str] = Field(default_factory=list, description="關鍵字")
    response_draft: Optional[str] = Field(None, description="AI 生成的回覆草稿")
    summary: Optional[str] = Field(None, description="問題摘要")
    suggested_tags: List[str] = Field(default_factory=list, description="建議標籤")
    # 🔥 新增：情緒分數欄位
    sentiment_score: Optional[float] = Field(None, description="情緒分數")


# ==================== 統計報表相關模型 ====================

class ReportFilter(BaseModel):
    """報表篩選條件"""
    course_id: Optional[str] = None
    class_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[QuestionStatus] = None


class QuestionStatistics(BaseModel):
    """提問統計"""
    total_questions: int
    pending_questions: int
    approved_questions: int
    rejected_questions: int
    average_difficulty: float
    questions_by_cluster: Dict[str, int]


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
    RECEIVED = "received"  # 收到的訊息
    SENT = "sent"  # 發送的訊息
    FAILED = "failed"  # 發送失敗


class LineMessageBase(BaseModel):
    """LINE 訊息基礎模型"""
    user_id: str = Field(..., description="LINE 使用者 ID")
    pseudonym: str = Field(..., description="去識別化後的使用者代號")
    message_type: LineMessageType = Field(..., description="訊息類型")
    direction: LineMessageDirection = Field(..., description="訊息方向")
    content: str = Field(..., description="訊息內容")
    
    # 關聯資訊
    course_id: Optional[str] = Field(None, description="關聯的課程ID")
    class_id: Optional[str] = Field(None, description="關聯的班級ID")
    question_id: Optional[str] = Field(None, description="關聯的提問ID")
    
    # LINE 相關
    line_message_id: Optional[str] = Field(None, description="LINE 訊息ID")
    reply_token: Optional[str] = Field(None, description="回覆 token")
    
    # 額外資訊
    error_message: Optional[str] = Field(None, description="錯誤訊息（如果發送失敗）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他元資料")


class LineMessageCreate(BaseModel):
    """建立 LINE 訊息記錄"""
    user_id: str
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

class ClusterBase(BaseModel):
    """AI 聚類主題模型 (用來描述一群相似的問題)"""
    course_id: str = Field(..., description="所屬課程ID")
    topic_label: str = Field(..., description="AI 生成的主題標籤 (例如: '迴圈語法錯誤')")
    summary: Optional[str] = Field(None, description="該主題的綜合摘要")
    keywords: List[str] = Field(default_factory=list, description="該聚類的代表性關鍵字")
    
    # 統計資訊
    question_count: int = Field(default=0, description="包含的問題數量")
    avg_difficulty: float = Field(default=0.0, description="平均難度")

    is_locked: bool = Field(default=False, description="是否已被人工鎖定 (若為 True，AI 重新分析時將保留此分類)")
    manual_label: Optional[str] = Field(None, description="人工手動設定的標籤名稱")

class ClusterCreate(ClusterBase):
    """建立聚類"""
    pass

class Cluster(ClusterBase):
    """聚類完整模型"""
    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True

class ClusterUpdate(BaseModel):
    """[新增] 用於 PATCH /ai/clusters/{id} 的請求模型"""
    topic_label: Optional[str] = Field(None, description="新的主題名稱")
    is_locked: bool = Field(default=True, description="更新後是否自動鎖定 (預設 True)")

class ClusterGenerateRequest(BaseModel):
    """[新增] 用於 POST /ai/clusters/generate 的請求模型"""
    course_id: str = Field(..., description="課程ID")
    max_clusters: int = Field(default=5, ge=1, le=20, description="希望 AI 分成的最大群組數量")