from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService


# ---- 数据库会话依赖 ----
# 每个请求自动获取一个独立的数据会话
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ---- JWT 鉴权 ----

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> str | None:
    """从 JWT token 中提取当前用户 ID（可选鉴权）。"""
    if token is None:
        return None
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )


async def require_user(
    user_id: Annotated[str | None, Depends(get_current_user)],
) -> str:
    """强制要求登录。"""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )
    return user_id


# ---- 认证服务依赖 ----

def get_auth_service(db: DBSession) -> AuthService:
    """获取认证服务实例（注入数据库会话）。"""
    return AuthService(db)


# ---- 文档服务依赖 ----

def get_document_service(db: DBSession) -> DocumentService:
    """获取文档服务实例（注入数据库会话）。"""
    return DocumentService(db)


# ---- 对话服务依赖 ----

def get_chat_service() -> ChatService:
    """获取对话服务实例（无状态，无需 DB session）。"""
    return ChatService.from_request()
