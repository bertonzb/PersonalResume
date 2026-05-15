from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User


class AuthService:
    """认证业务逻辑（对接 SQL Server 数据库）。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, email: str, password: str) -> User:
        """注册新用户。

        1. 检查邮箱是否已被注册
        2. 哈希密码后写入数据库
        """
        existing = await self.db.scalar(
            select(User).where(User.email == email)
        )
        if existing is not None:
            raise ValueError(f"邮箱已被注册: {email}")

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            role="user",
        )
        self.db.add(user)
        await self.db.flush()
        logger.info("user_registered", email=email, user_id=str(user.id))
        return user

    async def login(self, email: str, password: str) -> dict | None:
        """登录验证：查数据库 → 验密码 → 签发 JWT。"""
        logger.info("user_login_attempt", email=email)

        user = await self.db.scalar(
            select(User).where(User.email == email)
        )
        if user is None:
            logger.warning("user_not_found", email=email)
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning("password_mismatch", email=email)
            return None

        if not user.is_active:
            logger.warning("user_disabled", email=email)
            return None

        token = create_access_token(str(user.id))
        logger.info("user_login_success", email=email, user_id=str(user.id))
        return {"access_token": token, "token_type": "bearer"}

    async def get_user_by_id(self, user_id: str) -> User | None:
        """根据 ID 获取用户。"""
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None
        return await self.db.scalar(
            select(User).where(User.id == uid)
        )
