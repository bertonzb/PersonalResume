from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_token
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService

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


# ---- 文档服务依赖 ----

_document_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    """获取文档服务实例（单例）。"""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService.from_request()
    return _document_service


# ---- 对话服务依赖 ----

_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """获取对话服务实例（单例）。"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService.from_request()
    return _chat_service


# ---- 认证服务依赖 ----

_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """获取认证服务实例（单例）。"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_request()
    return _auth_service
