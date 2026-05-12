from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: UUID | None = Field(default=None, description="新建对话时不传")


class SourceItem(BaseModel):
    chunk_id: str
    content: str
    score: float


class ChatResponse(BaseModel):
    id: UUID
    reply: str
    sources: list[SourceItem] = Field(default_factory=list)
    steps: list[dict] = Field(default_factory=list)
    trace_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
