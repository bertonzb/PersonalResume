# =============================================================================
# 文件：app/models/message.py
# 作用：定义消息（Message）的 ORM 模型。
# 解释：每条消息属于一个 Conversation，记录角色（user/assistant）、
#       内容、RAG 检索来源、链路追踪 ID。
# =============================================================================
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Message(Base):
    """对话消息模型。"""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(20))  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    trace_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
