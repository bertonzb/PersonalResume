# 启用"延迟求值"类型注解（Python 3.10+ 特性）
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.document import Document
from app.rag.retriever import Retriever
from app.schemas.document import DocumentItem, DocumentListResponse


UPLOAD_DIR = Path("uploads")
ALLOWED_TYPES = {"application/pdf": "pdf", "text/plain": "txt", "text/markdown": "md"}


class DocumentService:
    """文档业务逻辑（对接 SQL Server 数据库）。"""

    def __init__(self, db: AsyncSession, retriever: Retriever | None = None) -> None:
        self.db = db
        self.retriever = retriever or Retriever()

    async def upload_document(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        user_id: uuid.UUID | None = None,
    ) -> Document:
        """上传并处理文档（文本提取 → 向量化 → 数据库写入）。"""

        # 1. 文件类型校验
        if content_type not in ALLOWED_TYPES:
            raise ValueError(f"不支持的文件类型: {content_type}")

        file_type = ALLOWED_TYPES[content_type]

        # 2. 保存到本地磁盘
        UPLOAD_DIR.mkdir(exist_ok=True)
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}.{file_type}"
        file_path.write_bytes(content)

        # 3. 提取文本
        text = self._extract_text(content, file_type)

        # 4. 创建 Document 并写入数据库
        doc = Document(
            id=uuid.uuid4(),
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=len(content),
            content=text,
            status="processing",
        )
        self.db.add(doc)
        await self.db.flush()

        # 5. 向量化入库
        chunk_count = await self.retriever.ingest_document(
            doc_id=doc.id,
            content=text,
        )

        # 6. 更新状态
        doc.chunk_count = chunk_count
        doc.status = "ready" if chunk_count > 0 else "empty"

        logger.info(
            "document_uploaded",
            doc_id=str(doc.id),
            filename=filename,
            chunk_count=chunk_count,
        )
        return doc

    async def list_documents(
        self,
        user_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> DocumentListResponse:
        """列出文档（从 SQL Server 分页查询）。"""
        stmt = select(Document)

        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)

        # 总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        # 分页
        stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        docs = result.scalars().all()

        items = [
            DocumentItem(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                status=doc.status,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
            )
            for doc in docs
        ]
        return DocumentListResponse(total=total, items=items)

    async def get_document(self, doc_id: uuid.UUID) -> DocumentItem | None:
        """根据 ID 获取文档详情。"""
        doc = await self.db.scalar(
            select(Document).where(Document.id == doc_id)
        )
        if doc is None:
            return None
        return DocumentItem(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
        )

    @staticmethod
    def _extract_text(content: bytes, file_type: str) -> str:
        """从文件内容中提取文本。"""

        if file_type == "txt" or file_type == "md":
            return content.decode("utf-8", errors="replace")

        if file_type == "pdf":
            try:
                import io
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(content))
                return "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            except Exception as e:
                logger.error("pdf_extraction_failed", error=str(e))
                return ""

        return ""
