from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_document_service
from app.core.logging import logger
from app.schemas.document import DocumentUploadResponse
from app.services.document_service import ALLOWED_TYPES, DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """上传文档（PDF/TXT/MD），自动向量化入库。"""

    # 文件类型校验
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}。支持: {', '.join(ALLOWED_TYPES.values())}",
        )

    # 文件大小校验
    content = await file.read()
    max_size = 20 * 1024 * 1024  # 20MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件过大: {len(content)} bytes。最大: {max_size} bytes",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名为空",
        )

    try:
        doc = await document_service.upload_document(
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("upload_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档处理失败",
        )

    return DocumentUploadResponse.model_validate(doc)
