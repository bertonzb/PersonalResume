from __future__ import annotations

from pydantic import Field

from app.agent.tools.base import BaseTool, ToolInput, ToolOutput
from app.rag.retriever import Retriever


class DocRetrievalInput(ToolInput):
    query: str = Field(..., description="检索查询文本")


class DocRetrievalOutput(ToolOutput):
    chunks: list[dict[str, str | float]]


class DocRetrievalTool(BaseTool):
    name = "doc_retrieval"
    description = (
        "在用户已上传的知识库中检索相关文档片段。"
        "当用户询问其文档中的内容时使用此工具。"
        "输入：query（搜索查询文本）"
        "输出：相关的文档片段列表"
    )

    def __init__(self, retriever: Retriever | None = None) -> None:
        self._retriever = retriever or Retriever()

    async def execute(self, params: DocRetrievalInput) -> DocRetrievalOutput:
        results = await self._retriever.retrieve(query=params.query, top_k=5)
        chunks = [
            {"chunk_id": r.chunk_id, "content": r.content, "score": r.score}
            for r in results
        ]
        return DocRetrievalOutput(chunks=chunks)
