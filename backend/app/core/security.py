# 启用"延迟求值"类型注解
from __future__ import annotations

# datetime：日期时间处理
# timedelta：时间间隔（如"30分钟后"）
# timezone：时区（utc 表示世界标准时间）
from datetime import datetime, timedelta, timezone

# python-jose 库：处理 JWT（JSON Web Token）
# jwt：JWT 的编码（生成）和解码（解析）
# JWTError：JWT 解析失败时抛出的异常
from jose import JWTError, jwt

# passlib 库：密码哈希处理
# CryptContext：密码上下文，管理哈希算法
from passlib.context import CryptContext

from app.config import get_settings

# ---- 密码哈希上下文 ----
# schemes=["bcrypt"]：使用 bcrypt 算法（目前最安全的密码哈希算法之一）
# deprecated="auto"：自动弃用旧算法
# 密码哈希 ≠ 加密：哈希是单向的，无法还原；加密可以解密还原
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ========== 密码哈希 ==========
def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码（bcrypt 限制 72 字节，超长密码截断）。

    为什么不用明文存密码？如果数据库泄露，攻击者拿不到原始密码。
    为什么用 bcrypt？bcrypt 自带"慢速"特性，暴力破解成本极高。
    """
    # bcrypt 只接受 bytes 类型，把字符串转为 UTF-8 编码的字节
    if isinstance(password, str):
        password = password.encode("utf-8")
    # bcrypt 限制最大 72 字节，超过则截断
    if isinstance(password, bytes) and len(password) > 72:
        password = password[:72]
    # 调用 passlib 的 hash 方法生成哈希值
    # 返回示例：$2b$12$Wr1QSlCs3i7ApSUKbOHyQO...
    return pwd_context.hash(password)


# ========== 密码验证 ==========
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确。

    passlib 会自动从哈希值中提取盐值（salt），
    用同样的算法重新计算，然后对比结果。
    """
    return pwd_context.verify(plain_password, hashed_password)


# ========== JWT Token 生成 ==========
def create_access_token(user_id: str, expires_minutes: int | None = None) -> str:
    """创建 JWT access token（登录凭证）。

    JWT 由三部分组成：Header.Payload.Signature
    - Header：算法类型（HS256）
    - Payload：存储的数据（用户 ID、过期时间）
    - Signature：签名，防止篡改

    参数：
        user_id：用户唯一标识
        expires_minutes：有效期（分钟），不传则用配置的默认值
    """
    settings = get_settings()
    # 计算过期时间：如果没传就用配置的默认过期时间
    expire_minutes = expires_minutes or settings.jwt_expire_minutes
    # datetime.now(timezone.utc)：当前 UTC 时间
    # timedelta(minutes=...)：加上 N 分钟
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    # Payload（载荷）：JWT 中存储的数据
    payload = {
        "sub": user_id,          # sub（subject）：主体，通常存用户 ID
        "exp": expire,           # exp（expiration）：过期时间
        "iat": datetime.now(timezone.utc),  # iat（issued at）：签发时间
    }
    # 用密钥签名，生成最终的 JWT 字符串
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ========== JWT Token 解析 ==========
def decode_token(token: str) -> dict:
    """解码 JWT token，返回 payload。

    如果 token 过期或被篡改，会抛出 ValueError。
    """
    settings = get_settings()
    try:
        # jwt.decode：验证签名并解析 payload
        # algorithms=[...]：允许的加密算法列表
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        # 签名无效、过期等都归为"无效 token"
        raise ValueError("无效的 token")


# ======== API Key 加解密 ========
# 用途：用户可能在前端设置页保存自己的第三方便 API Key（如 Tavily Key）
# 这些 Key 需要加密存储到数据库，不能明文保存

# cryptography 库：专业的加密库
# Fernet：对称加密，基于 AES-128-CBC + HMAC 签名
from cryptography.fernet import Fernet
# base64：Base64 编解码，把二进制数据转成可读字符串
import base64
# hashlib：哈希算法，这里用 SHA-256 把密码派生为加密密钥
import hashlib


def _get_fernet() -> Fernet:
    """获取 Fernet 加密器实例（内部方法）。

    为什么需要这个函数？
    Fernet 要求 32 字节的 Base64 编码密钥，但用户配置的加密口令可能是任意长度。
    所以：
        用户口令 → SHA-256 哈希 → 固定的 32 字节 → Base64 编码 → Fernet 密钥
    """
    settings = get_settings()
    # hashlib.sha256(...)：SHA-256 哈希，无论输入多长，输出固定 32 字节
    # digest()：获取原始字节
    key = hashlib.sha256(settings.encryption_key.encode()).digest()
    # base64.urlsafe_b64encode：URL 安全的 Base64 编码
    fernet_key = base64.urlsafe_b64encode(key)
    # 创建 Fernet 加密器实例
    return Fernet(fernet_key)


# ========== 加密 API Key ==========
def encrypt_api_key(plain_key: str) -> str:
    """使用 AES-GCM 加密 API Key。

    明文 → Fernet 加密 → 密文字符串
    """
    f = _get_fernet()
    # .encode()：字符串转字节，因为 Fernet 只处理字节
    # .decode()：加密结果是字节，转回字符串方便存储
    return f.encrypt(plain_key.encode()).decode()


# ========== 解密 API Key ==========
def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key。

    密文字符串 → Fernet 解密 → 明文
    """
    f = _get_fernet()
    return f.decrypt(encrypted_key.encode()).decode()
