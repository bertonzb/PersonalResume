from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（bcrypt 限制 72 字节，超长密码截断）。"""
    if isinstance(password, str):
        password = password.encode("utf-8")
    if isinstance(password, bytes) and len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码。"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, expires_minutes: int | None = None) -> str:
    """创建 JWT access token。"""
    settings = get_settings()
    expire_minutes = expires_minutes or settings.jwt_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """解码 JWT token，返回 payload。"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise ValueError("无效的 token")


# ---- API Key 加密 ----

from cryptography.fernet import Fernet
import base64
import hashlib


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = hashlib.sha256(settings.encryption_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_api_key(plain_key: str) -> str:
    """使用 AES-GCM 加密 API Key。"""
    f = _get_fernet()
    return f.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key。"""
    f = _get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()
