from __future__ import annotations

import uuid
from pathlib import Path

from app.core.logging import logger
from app.models.document import Document
from app.rag.retriever import Retriever
from app.schemas.document import DocumentItem, DocumentListResponse


UPLOAD_DIR = Path("uploads")
ALLOWED_TYPES = {"application/pdf": "pdf", "text/plain": "txt", "text/markdown": "md"}


class DocumentService:
    """文档业务逻辑。"""

    def __init__(self, retriever: Retriever | None = None) -> None:
        self.retriever = retriever or Retriever()

    @classmethod
    def from_request(cls) -> "DocumentService":
        return cls()

    async def upload_document(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        user_id: uuid.UUID | None = None,
    ) -> Document:
        """上传并处理文档。"""
        if content_type not in ALLOWED_TYPES:
            raise ValueError(f"不支持的文件类型: {content_type}")

        file_type = ALLOWED_TYPES[content_type]

        # 保存文件到本地
        UPLOAD_DIR.mkdir(exist_ok=True)
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}.{file_type}"
        file_path.write_bytes(content)

        # 提取文本
        text = self._extract_text(content, file_type)

        # 创建文档记录（临时用内存对象，后续接入数据库）
        doc = Document(
            id=uuid.uuid4(),
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=len(content),
            content=text,
            status="processing",
        )

        # 向量化入库
        chunk_count = await self.retriever.ingest_document(
            doc_id=doc.id,
            content=text,
        )

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
        """列出文档（暂用内存列表）。"""
        # 后续接入数据库查询
        return DocumentListResponse(total=0, items=[])

    async def get_document(self, doc_id: uuid.UUID) -> DocumentItem | None:
        """获取单个文档。"""
        return None

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
