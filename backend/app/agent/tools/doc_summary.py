from __future__ import annotations

from pydantic import Field

from app.agent.tools.base import BaseTool, ToolInput, ToolOutput
from app.config import get_settings
from app.core.logging import logger


class DocSummaryInput(ToolInput):
    content: str = Field(..., description="需要总结的文档内容")


class DocSummaryOutput(ToolOutput):
    summary: str
    key_points: list[str]


class DocSummaryTool(BaseTool):
    name = "doc_summary"
    description = (
        "对指定的文档内容生成结构化摘要和关键要点。"
        "当用户需要总结或概括某篇文档的内容时使用此工具。"
        "输入：content（文档文本内容）"
        "输出：summary（摘要文本）、key_points（关键要点列表）"
    )

    async def execute(self, params: DocSummaryInput) -> DocSummaryOutput:
        settings = get_settings()

        if not settings.llm_api_key:
            logger.warning("doc_summary_no_api_key")
            return DocSummaryOutput(
                summary=f"（无法生成摘要——未配置 API Key）\n内容长度: {len(params.content)} 字符",
                key_points=["请配置 LLM API Key 后重试"],
            )

        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                temperature=0.2,
            )
            prompt = (
                "请对以下文档内容生成摘要，要求：\n"
                "1. 用 2-3 句话概括核心内容\n"
                "2. 列出 3-5 个关键要点\n\n"
                f"## 文档内容\n{params.content[:4000]}"
            )
            response = await llm.ainvoke(prompt)
            text = response.content if hasattr(response, "content") else str(response)

            # 简单解析
            lines = text.strip().split("\n")
            summary = lines[0] if lines else text
            key_points = [l.strip("- ") for l in lines[1:] if l.strip()][:5]

            return DocSummaryOutput(summary=summary, key_points=key_points)
        except Exception as e:
            logger.error("doc_summary_failed", error=str(e))
            return DocSummaryOutput(
                summary=f"摘要生成失败: {e}",
                key_points=[],
            )
