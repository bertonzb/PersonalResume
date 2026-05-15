# =============================================================================
# 文件：app/models/document.py
# 作用：定义文档（Document）的数据库 ORM 模型。
# 解释：Document 代表用户上传到知识库的文件。每上传一个文件（PDF、TXT 等），
#       就会在数据库中创建一条 Document 记录，记录文件名、类型、大小、
#       解析后的文本内容、处理状态等。
# =============================================================================

# 延迟求值的类型注解（让类型提示中的 uuid.UUID 在运行时不会被立即解析）。
from __future__ import annotations

# uuid：生成全局唯一 ID（Python 标准库）。
import uuid

# Optional：类型提示工具，表示某个值可以是某种类型，也可以是 None。
#   例如 Optional[uuid.UUID] 等价于 uuid.UUID | None。
from typing import Optional

# ---- 导入 SQLAlchemy 的列类型 ----
# Integer：  整数类型。
# String：   变长字符串类型，括号里是最大长度。
# Text：     长文本类型（没有长度限制），适合存储文档的全文内容。
from sqlalchemy import Integer, String, Text

# Mapped：      声明式的类型标注方式，告诉 SQLAlchemy 这一列存什么类型。
# mapped_column：定义列的数据库属性（是否索引、是否可为空等）。
from sqlalchemy.orm import Mapped, mapped_column

# 导入父类 BaseModel，Document 会继承 id、created_at、updated_at 三个公共字段。
from app.models.base import BaseModel


# ---- Document 模型 ----
class Document(BaseModel):
    # __tablename__：指定这个模型对应的数据库表名。
    #   如果不写，SQLAlchemy 会默认用类名的小写形式（即 document）。
    #   显式指定复数形式 documents 更符合数据库命名惯例。
    __tablename__ = "documents"

    # user_id：文档所有者的用户 ID。
    #   Mapped[Optional[uuid.UUID]]：可以是 UUID，也可以是 None。
    #   index=True：为这一列创建数据库索引，按用户 ID 查询文档时速度更快。
    #   nullable=True：允许为空（即文档可以不关联到特定用户，比如公共文档）。
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(index=True, nullable=True)

    # filename：上传文件的原始名称（如 学习笔记.pdf）。
    #   String(255)：数据库列类型为 VARCHAR(255)，最多存储 255 个字符。
    filename: Mapped[str] = mapped_column(String(255))

    # file_type：文件类型 / 扩展名（如 pdf、txt、docx）。
    #   String(20)：最多 20 个字符。
    file_type: Mapped[str] = mapped_column(String(20))

    # file_size：文件大小，单位是字节（bytes）。
    #   Integer：数据库列类型为整数。
    file_size: Mapped[int] = mapped_column(Integer)

    # content：文件解析后的纯文本内容。
    #   Text：数据库列类型为 TEXT（长文本，没有长度上限）。
    #   default=：默认值为空字符串（刚上传但还没解析完成的文档，content 为空）。
    content: Mapped[str] = mapped_column(Text, default="")

    # status：文档的处理状态。
    #   可选值：pending（等待处理）、processing（处理中）、
    #           completed（完成）、failed（失败）。
    #   String(20)：最多 20 个字符。
    #   default=pending：刚上传时状态为等待处理。
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # chunk_count：文档被切分成多少个片段（chunk）。
    #   chunk 是 RAG（检索增强生成）系统的核心概念：
    #   大文档会被切分成若干小段，每段是一个 chunk，方便后续检索。
    #   Integer：整数类型。
    #   default=0：新文档还没切分，chunk 数量为 0。
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
