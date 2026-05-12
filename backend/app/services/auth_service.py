from __future__ import annotations

import uuid

from app.core.logging import logger
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User


class AuthService:
    """认证业务逻辑。"""

    @classmethod
    def from_request(cls) -> "AuthService":
        return cls()

    def register(self, email: str, password: str) -> User:
        """注册新用户。"""
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            role="user",
        )
        logger.info("user_registered", email=email, user_id=str(user.id))
        return user

    def login(self, email: str, password: str) -> dict | None:
        """登录验证，返回 token。"""
        # 后续接入数据库后改为从 DB 查询
        # 目前返回模拟结果
        logger.info("user_login_attempt", email=email)

        # 开发阶段：任何用户名+密码都行，生成 token
        token = create_access_token(str(uuid.uuid4()))
        logger.info("user_login_success", email=email)
        return {"access_token": token, "token_type": "bearer"}

    def get_user_by_id(self, user_id: str) -> User | None:
        """根据 ID 获取用户。"""
        return None
