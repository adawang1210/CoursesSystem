"""
安全相關工具
包含密碼加密、JWT token 生成、去識別化等功能
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from ..config import settings


# 密碼加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== 密碼處理 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密碼雜湊"""
    return pwd_context.hash(password)


# ==================== JWT Token ====================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    建立 JWT access token
    
    Args:
        data: 要編碼的資料 (通常包含 user_id, email 等)
        expires_delta: token 過期時間
    
    Returns:
        JWT token 字串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解碼 JWT token
    
    Args:
        token: JWT token 字串
    
    Returns:
        解碼後的資料，如果無效則返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ==================== 去識別化處理 ====================

def generate_pseudonym(line_user_id: str, salt: Optional[str] = None) -> str:
    """
    生成去識別化的使用者代號 (pseudonym)
    
    使用 SHA256 雜湊演算法對 Line User ID 進行不可逆加密。
    加入 salt 可以增加安全性，防止彩虹表攻擊。
    
    Args:
        line_user_id: Line User ID (原始識別碼)
        salt: 鹽值 (可選，預設使用環境變數中的值)
    
    Returns:
        去識別化後的代號 (64 字元的十六進位字串)
    
    Example:
        >>> generate_pseudonym("U1234567890abcdef")
        'a1b2c3d4e5f6...'  # 64 字元的 SHA256 雜湊值
    """
    if salt is None:
        salt = settings.PSEUDONYM_SALT
    
    # 組合 line_user_id 和 salt
    data_to_hash = f"{line_user_id}{salt}"
    
    # 使用 SHA256 進行雜湊
    pseudonym = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
    
    return pseudonym


def generate_short_pseudonym(line_user_id: str, length: int = 16) -> str:
    """
    生成短版去識別化代號 (方便顯示)
    
    Args:
        line_user_id: Line User ID
        length: 代號長度 (預設 16)
    
    Returns:
        短版去識別化代號
    """
    full_pseudonym = generate_pseudonym(line_user_id)
    return full_pseudonym[:length]


# ==================== 資料驗證 ====================

def validate_pseudonym(pseudonym: str) -> bool:
    """
    驗證 pseudonym 格式是否正確
    
    Args:
        pseudonym: 待驗證的 pseudonym
    
    Returns:
        是否為有效的 pseudonym
    """
    # SHA256 雜湊值長度為 64 個十六進位字元
    if len(pseudonym) not in [16, 64]:
        return False
    
    # 檢查是否只包含十六進位字元
    try:
        int(pseudonym, 16)
        return True
    except ValueError:
        return False


# ==================== 資料遮罩 ====================

def mask_email(email: str) -> str:
    """
    遮罩電子郵件地址
    
    Example:
        user@example.com -> u***@example.com
    """
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 1)
    
    return f"{masked_local}@{domain}"


def mask_line_user_id(line_user_id: str, visible_chars: int = 4) -> str:
    """
    遮罩 Line User ID
    
    Example:
        U1234567890abcdef -> U123***
    """
    if len(line_user_id) <= visible_chars:
        return line_user_id
    
    return line_user_id[:visible_chars] + '***'

