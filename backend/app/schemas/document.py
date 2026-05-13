from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    created_at: datetime | None = Field(default=None)

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentUploadResponse]


class DocumentItem(BaseModel):
    """文档列表单项。"""

    id: UUID
    filename: str
    file_type: str
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
