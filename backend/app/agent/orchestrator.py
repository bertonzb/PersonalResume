from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI

from app.agent.tools.doc_retrieval import DocRetrievalInput, DocRetrievalTool
from app.agent.tools.doc_summary import DocSummaryInput, DocSummaryTool
from app.agent.tools.web_search import WebSearchInput, WebSearchTool
from app.config import get_settings
from app.core.logging import logger


@dataclass
class AgentStep:
    """单步执行记录。"""

    step_number: int
    tool_name: str
    input: str
    output: str
    status: str  # thinking | acting | observing | done | error
    duration_ms: float


@dataclass
class AgentResult:
    """Agent 执行结果。"""

    reply: str
    steps: list[AgentStep]
    sources: list[dict[str, Any]]
    trace_id: str


class AgentOrchestrator:
    """Agent 主编排器，管理工具调用和多步推理。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.1,
        )
        self.tools = self._build_tools()
        self._agent = self._create_agent()

    def _build_tools(self) -> list[StructuredTool]:
        """构建 LangChain Tool 列表。"""
        doc_retrieval = DocRetrievalTool()
        doc_summary = DocSummaryTool()
        web_search = WebSearchTool()

        return [
            StructuredTool.from_function(
                name=doc_retrieval.name,
                description=doc_retrieval.description,
                args_schema=DocRetrievalInput,
                func=None,
                coroutine=self._wrap_tool(doc_retrieval),
            ),
            StructuredTool.from_function(
                name=doc_summary.name,
                description=doc_summary.description,
                args_schema=DocSummaryInput,
                func=None,
                coroutine=self._wrap_tool(doc_summary),
            ),
            StructuredTool.from_function(
                name=web_search.name,
                description=web_search.description,
                args_schema=WebSearchInput,
                func=None,
                coroutine=self._wrap_tool(web_search),
            ),
        ]

    def _wrap_tool(self, tool: Any):
        """包装 Tool 为标准协程函数。"""

        async def _run(**kwargs):
            input_schema = kwargs
            result = await tool.execute(input_schema)
            return result.model_dump_json()

        return _run

    def _create_agent(self):
        system_prompt = (
            "你是一个个人知识库深度研究助手 DeepScribe。你可以使用以下工具：\n"
            "- doc_retrieval: 在用户的知识库中检索文档\n"
            "- web_search: 搜索互联网获取最新信息\n"
            "- doc_summary: 生成文档摘要和关键要点\n\n"
            "当用户提出问题时：\n"
            "1. 先判断问题类型，选择合适的工具\n"
            "2. 如果问题与用户的知识库相关，优先使用 doc_retrieval\n"
            "3. 如果需要最新信息或知识库中无相关内容，使用 web_search\n"
            "4. 对于多步骤的研究任务，依次调用多个工具\n"
            "5. 最后整合所有信息，给出结构化的回答\n\n"
            "请用中文回答。如果使用工具，请说明你使用了哪些工具。"
        )

        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
        )

    async def run(
        self,
        user_id: uuid.UUID | None = None,
        message: str = "",
        conversation_id: uuid.UUID | None = None,
    ) -> AgentResult:
        """执行 Agent 任务。"""
        import time

        trace_id = str(uuid.uuid4())
        steps: list[AgentStep] = []

        logger.info(
            "agent_run_started",
            trace_id=trace_id,
            user_id=str(user_id) if user_id else None,
            message_length=len(message),
        )

        try:
            t0 = time.monotonic()
            result = await self._agent.ainvoke({"input": message, "messages": []})
            duration_ms = (time.monotonic() - t0) * 1000

            # LangChain 1.x: 返回 messages 列表，最后一条是 AI 回复
            messages = result.get("messages", [])
            reply = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and str(getattr(msg, "type", "")) == "ai":
                    reply = str(msg.content)
                    break
            if not reply:
                reply = str(result.get("output", "Agent 未返回结果"))

            # 解析中间步骤（tool_calls 在 AI message 中）
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        steps.append(
                            AgentStep(
                                step_number=len(steps) + 1,
                                tool_name=str(tc.get("name", "unknown")),
                                input=str(tc.get("args", {}))[:200],
                                output="",
                                status="done",
                                duration_ms=0,
                            )
                        )

            logger.info(
                "agent_run_completed",
                trace_id=trace_id,
                step_count=len(steps),
                total_duration_ms=round(duration_ms),
            )

        except Exception as e:
            logger.error("agent_run_failed", trace_id=trace_id, error=str(e))
            reply = f"抱歉，研究过程中出现错误: {str(e)}"

        return AgentResult(
            reply=reply,
            steps=steps,
            sources=[],
            trace_id=trace_id,
        )
