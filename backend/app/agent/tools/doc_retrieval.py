"""
===============================================================================
文件名称: doc_retrieval.py
所属模块: app.agent.tools (Agent 工具模块)
项目角色: 实现"文档检索"工具 —— 在用户上传的知识库中搜索相关文档片段。

当用户提出一个问题时，Agent 可能会调用本工具去用户的文档库中查找相关内容。
这个工具是 RAG（检索增强生成，Retrieval-Augmented Generation）流程的核心环节：
先从知识库中检索出最相关的文档片段，然后将这些片段作为上下文提供给 LLM，
从而让 LLM 能够基于用户自己的文档内容来回答问题。

工作流程：
  用户提问  -->  Agent 决定调用 doc_retrieval  -->  向量检索找到 top-5 相关片段
  -->  返回片段列表给 LLM  -->  LLM 结合片段内容生成答案

关键概念：
  - Pydantic Field: 给数据模型的字段添加元信息（描述、默认值等）。
    Field(...) 中的 ... 是 Ellipsis，表示该字段是"必填"的。
  - Retriever: 本项目自定义的检索器，负责与向量数据库交互。
  - top-k 检索: 从知识库中返回语义最相关的 k 个文档片段。
===============================================================================
"""

# ---------------------------------------------------------------------------
# (1) 导入区
# ---------------------------------------------------------------------------

# from __future__ import annotations: 延迟类型注解求值，支持前向引用。
# 例如可以在类内使用自身类型作为字段类型。
from __future__ import annotations

# Field: Pydantic 提供的字段描述函数。
# 用法: my_field: str = Field(..., description="字段说明")
#   - 第一个参数 ... 表示该字段为"必填"（无默认值）
#   - description 参数会出现在 JSON Schema 中，LLM 可以读取到这些描述
#   - 此外还支持 default（默认值）、min_length（最小长度）等约束
from pydantic import Field

# 从工具基类模块导入三个基类：
#   - BaseTool: 所有工具必须继承的抽象基类
#   - ToolInput: 入参基类（Pydantic 模型）
#   - ToolOutput: 出参基类（Pydantic 模型）
from app.agent.tools.base import BaseTool, ToolInput, ToolOutput

# Retriever: 本项目的文档检索器。
# 它封装了与向量数据库（如 Chroma、FAISS 等）的交互逻辑，
# 负责将用户的查询文本转换为向量，然后在向量空间中搜索最相似的内容。
from app.rag.retriever import Retriever


# ---------------------------------------------------------------------------
# (2) DocRetrievalInput - 文档检索的入参定义
# ---------------------------------------------------------------------------

class DocRetrievalInput(ToolInput):
    """
    文档检索工具的输入参数。

    继承自 ToolInput（而 ToolInput 继承自 Pydantic 的 BaseModel），
    因此自动获得了类型校验和序列化能力。

    字段说明：
        query (str): 用户想要搜索的查询文本。
                     例如 "项目中使用的是什么数据库？"
    """
    # Field(...) 中的 ... 是 Ellipsis（省略号），表示"必填、无默认值"。
    # description 参数是给 LLM 看的，告诉 LLM 这个字段应该填入什么内容。
    # Pydantic 会自动生成 JSON Schema，LLM 会读取 Schema 中的 description。
    query: str = Field(..., description="检索查询文本")


# ---------------------------------------------------------------------------
# (3) DocRetrievalOutput - 文档检索的出参定义
# ---------------------------------------------------------------------------

class DocRetrievalOutput(ToolOutput):
    """
    文档检索工具的输出结果。

    字段说明：
        chunks (list[dict[str, str | float]]): 检索到的文档片段列表。
            每个片段是一个字典，包含：
              - "chunk_id" (str): 片段唯一标识
              - "content" (str): 片段的文本内容
              - "score" (float): 语义相似度分数（分数越高表示越相关）
    """
    # list[dict[str, str | float]] 的详细解释：
    #   - list[...] 表示这是一个列表
    #   - dict[str, str | float] 表示字典的键是 str 类型，
    #     值可以是 str 或 float 类型（用 | 表示"联合类型"）
    chunks: list[dict[str, str | float]]


# ---------------------------------------------------------------------------
# (4) DocRetrievalTool - 文档检索工具的具体实现
# ---------------------------------------------------------------------------

class DocRetrievalTool(BaseTool):
    """
    文档检索工具。

    在用户已上传的知识库中进行语义检索，返回最相关的文档片段。
    这是 RAG（检索增强生成）架构中的核心检索环节。

    继承自 BaseTool，必须实现 execute() 方法。

    类属性：
        name: 工具名称，Agent 通过此名称来调度工具
        description: LLM 可读的工具说明，包含触发条件、输入格式、输出格式
    """

    # name: 工具的唯一标识名称。
    # Agent 编排器使用此名称来区分不同的工具。
    name = "doc_retrieval"

    # description: 给 LLM 看的工具使用说明。
    # 括号 (...) 用于将多行字符串隐式拼接为一个字符串（Python 语法特性）。
    # LLM 会阅读这段描述，决定在什么情况下调用这个工具。
    description = (
        "在用户已上传的知识库中检索相关文档片段。"
        "当用户询问其文档中的内容时使用此工具。"
        "输入：query（搜索查询文本）"
        "输出：相关的文档片段列表"
    )

    def __init__(self, retriever: Retriever | None = None) -> None:
        """
        初始化文档检索工具。

        参数：
            retriever (Retriever | None): 可选的检索器实例。
                - 如果传入了一个 Retriever 实例，就用它
                - 如果传入 None（或不传），则自动创建一个新的默认 Retriever
                - 这被称为"依赖注入"模式，方便测试时可以传入 mock 对象

        返回值：
            None（__init__ 总是返回 None）

        内部逻辑：
            使用 or 运算符的短路特性：如果 retriever 是真值（非 None），
            就用 retriever；否则调用 Retriever() 创建一个新实例。
        """
        # self._retriever: 下划线前缀 _ 表示这是一个"受保护的"内部属性，
        # Python 约定中 _ 前缀表示"请在类外部不要直接访问"。
        # retriever or Retriever(): Python 的 or 运算符短路求值。
        #   如果 retriever 不为 None，返回 retriever 本身；
        #   如果 retriever 是 None（假值），则执行并返回 Retriever() 的结果。
        self._retriever = retriever or Retriever()

    async def execute(self, params: DocRetrievalInput) -> DocRetrievalOutput:
        """
        执行文档检索（异步方法）。

        async: 声明这是一个异步方法（协程）。调用时需要用 await，
               执行过程中遇到 I/O 操作（如数据库查询）会释放控制权给事件循环。

        执行流程：
            1. 调用 Retriever.retrieve() 进行语义搜索
            2. 取前 5 个最相关的结果（top_k=5）
            3. 将结果列表中的每个检索结果转换为字典
            4. 封装为 DocRetrievalOutput 并返回

        参数：
            params (DocRetrievalInput): 包含 query 字段的输入对象

        返回：
            DocRetrievalOutput: 包含 chunks 列表的输出对象
        """
        # 调用检索器的 retrieve 方法，传入查询文本和 top_k 参数
        #   - query=params.query: 从输入对象中取出用户的查询字符串
        #   - top_k=5: 只返回最相似的 5 个文档片段
        # await: 等待异步检索操作完成
        results = await self._retriever.retrieve(query=params.query, top_k=5)

        # 列表推导式 (list comprehension): 遍历 results，将每个检索结果 r
        # 转换为字典格式。这是一种 Python 中简洁高效的数据转换写法。
        # 语法: [表达式 for 变量 in 可迭代对象]
        chunks = [
            # 每个结果 r 是一个包含 chunk_id、content、score 的对象
            {"chunk_id": r.chunk_id, "content": r.content, "score": r.score}
            for r in results
        ]

        # 将转换后的 chunks 列表封装为 DocRetrievalOutput 对象并返回。
        # DocRetrievalOutput(chunks=chunks) 会自动进行 Pydantic 类型校验。
        return DocRetrievalOutput(chunks=chunks)
