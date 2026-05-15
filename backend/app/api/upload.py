# =============================================================================
# 文件：app/api/upload.py
# 作用：文档上传接口。接收前端上传的文件，校验后交给 Service 层处理。
#       整个上传流程：前端选文件 → 发 POST 请求 → 本文件接收 → service 层处理
# =============================================================================

from __future__ import annotations

# APIRouter：创建路由器的类
# Depends：FastAPI 的依赖注入工具
# File：声明参数是一个上传文件
# HTTPException：抛出一个 HTTP 错误响应
# UploadFile：上传文件的类型（包含文件名、文件内容、MIME 类型等）
# status：HTTP 状态码常量（如 200、400、500）
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

# get_document_service：获取 DocumentService 实例的工厂函数
from app.api.deps import get_document_service
from app.core.logging import logger
# DocumentUploadResponse：上传成功后返回的数据格式
from app.schemas.document import DocumentUploadResponse
# DocumentService：文档业务逻辑
# ALLOWED_TYPES：允许上传的文件类型映射表
from app.services.document_service import ALLOWED_TYPES, DocumentService

# 创建路由器
# prefix="/documents"：所有接口地址都以 /documents 开头
# 最终访问：/api/v1/documents/upload
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    # File(...)：告诉 FastAPI "从请求中提取上传的文件"
    # ...（Ellipsis）表示这个参数是必需的
    file: UploadFile = File(...),
    # Depends(get_document_service)：依赖注入
    # FastAPI 自动调用 get_document_service() 创建 DocumentService 实例
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """上传文档（PDF/TXT/MD），自动向量化入库。"""

    # ===== 校验 1：文件类型 =====
    # file.content_type：浏览器发送的文件 MIME 类型
    # 例如 PDF 文件是 "application/pdf"，TXT 是 "text/plain"
    if file.content_type not in ALLOWED_TYPES:
        # HTTPException：抛出 HTTP 错误给前端
        # status_code=400：坏请求（客户端传了不支持的文件类型）
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}。支持: {', '.join(ALLOWED_TYPES.values())}",
        )

    # ===== 校验 2：文件大小 =====
    # await file.read()：异步读取文件的所有字节内容
    # await 是"等待"，在此期间服务器可以去处理其他请求
    content = await file.read()
    # 20 * 1024 * 1024 = 20,971,520 字节 = 20MB
    max_size = 20 * 1024 * 1024  # 20MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件过大: {len(content)} bytes。最大: {max_size} bytes",
        )

    # ===== 校验 3：文件名为空 =====
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名为空",
        )

    # ===== 调用 Service 层处理文档 =====
    try:
        # 把文件信息传给 Service 层的 upload_document 方法
        # Service 层负责：保存文件 → 提取文本 → 向量化入库
        doc = await document_service.upload_document(
            filename=file.filename,       # 原始文件名
            content_type=file.content_type, # 文件 MIME 类型
            content=content,               # 文件字节内容
        )
    except ValueError as e:
        # 业务逻辑错误（如不支持的文件类型）→ 返回 400
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # 其他未预期的错误（如向量数据库故障、AI 服务故障）→ 返回 500
        logger.error("upload_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档处理失败",
        )

    # 把 Service 层返回的 Document 对象转成 API 响应格式
    # model_validate：从 ORM 对象创建 Pydantic Schema 实例
    return DocumentUploadResponse.model_validate(doc)
