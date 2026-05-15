# =============================================================================
# 文件：app/schemas/document.py
# 作用：定义文档相关的 API 请求和响应数据结构（Pydantic Schema）。
# 解释：本文件定义的 Schema 用于：
#       1. 文档上传后的响应（告诉前端上传成功了，文档的 ID 是什么等）。
#       2. 文档列表的响应（展示用户所有已上传的文档）。
#       3. 文档列表中的单项（列表里每个元素的结构）。
# =============================================================================

# 延迟求值的类型注解。
from __future__ import annotations

# datetime：Python 标准库的日期时间类。
from datetime import datetime

# UUID：Python 标准库的 UUID 类型。
from uuid import UUID

# BaseModel：Pydantic 基类，用于数据校验和 JSON 序列化。
# Field：用于给字段添加额外的元数据（描述、默认值等）。
from pydantic import BaseModel, Field


# ---- 文档上传响应 ----

class DocumentUploadResponse(BaseModel):
    # id：新创建的文档的唯一标识（UUID）。
    id: UUID

    # filename：上传文件的原始名称。
    filename: str

    # file_type：文件类型/扩展名（如 pdf、txt）。
    file_type: str

    # file_size：文件大小（字节数）。
    file_size: int

    # status：文档处理状态（pending / processing / completed / failed）。
    status: str

    # chunk_count：文档被切分成的文本块数量。
    chunk_count: int

    # created_at：文档上传时间。
    #   datetime | None：可能是 datetime 对象，也可能是 None。
    #   Field(default=None)：如果在创建响应时没有提供时间，默认为 None。
    #   为什么允许 None？因为 POST 请求返回时，数据库可能还没写完，
    #   或者前端不需要这个字段时可以不传。
    created_at: datetime | None = Field(default=None)

    # model_config：Pydantic v2 的配置字典。
    # {"from_attributes": True} 允许直接从 ORM 对象（SQLAlchemy 模型实例）
    # 的属性中读取值来构造这个 Schema。
    # 例如：doc = db.query(Document).first()
    #       response = DocumentUploadResponse.model_validate(doc)
    model_config = {"from_attributes": True}


# ---- 文档列表响应 ----

class DocumentListResponse(BaseModel):
    # total：文档的总数量（用于前端分页显示"共 X 条"）。
    total: int

    # items：文档列表。
    #   list[DocumentUploadResponse]：每个元素都是 DocumentUploadResponse 类型。
    #   这里复用了 DocumentUploadResponse 的定义，
    #   而不是重新定义一个新的 Schema。
    items: list[DocumentUploadResponse]


# ---- 文档列表单项 ----

class DocumentItem(BaseModel):
    """文档列表单项。"""

    # id：文档唯一标识（UUID）。
    id: UUID

    # filename：文件名。
    filename: str

    # file_type：文件类型（pdf / txt / docx 等）。
    file_type: str

    # status：处理状态。
    status: str

    # chunk_count：文本块数量。
    chunk_count: int

    # created_at：上传时间。
    created_at: datetime

    # from_attributes=True：允许从 SQLAlchemy ORM 对象直接构造此 Schema。
    model_config = {"from_attributes": True}
