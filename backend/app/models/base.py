from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类。"""
    pass


class BaseModel(Base):
    """所有 ORM 模型的公共字段。"""

    __abstract__ = True

    # Uuid：SQLAlchemy 2.0 通用 UUID 类型，自动适配不同数据库
    #   PostgreSQL → UUID
    #   SQL Server → UNIQUEIDENTIFIER
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    # DateTime(timezone=True)：自动适配
    #   PostgreSQL → TIMESTAMPTZ
    #   SQL Server → DATETIME2
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
