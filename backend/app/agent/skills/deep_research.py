from __future__ import annotations

import time

from app.agent.orchestrator import AgentStep
from app.agent.skills.base import BaseSkill, SkillResult
from app.agent.tools.doc_retrieval import DocRetrievalInput, DocRetrievalTool
from app.agent.tools.doc_summary import DocSummaryInput, DocSummaryTool
from app.agent.tools.web_search import WebSearchInput, WebSearchTool
from app.core.logging import logger


class DeepResearchSkill(BaseSkill):
    """深度研究 Skill：拆解问题 → 多源搜索 → 对比整合 → 输出结构化提纲。"""

    name = "deep_research"
    description = (
        "对复杂的研究问题进行深度分析。流程包括：\n"
        "1. 拆解研究问题为多个子问题\n"
        "2. 对每个子问题在知识库和互联网中搜索\n"
        "3. 对比整合不同来源的信息\n"
        "4. 输出结构化的研究报告提纲\n"
        "当用户明确需要'深度研究'或'深入分析'某个主题时触发。"
    )

    def __init__(self) -> None:
        self.doc_retrieval = DocRetrievalTool()
        self.web_search = WebSearchTool()
        self.doc_summary = DocSummaryTool()

    async def execute(self, context: dict) -> SkillResult:
        topic = context.get("topic", "")
        if not topic:
            return SkillResult(output="请提供研究主题", steps=[])

        steps: list[AgentStep] = []
        t0 = time.monotonic()

        logger.info("deep_research_started", topic=topic)

        # Step 1: 搜索知识库
        doc_results = await self.doc_retrieval.execute(DocRetrievalInput(query=topic))
        steps.append(
            AgentStep(
                step_number=1,
                tool_name="doc_retrieval",
                input=topic,
                output=f"找到 {len(doc_results.chunks)} 个相关片段",
                status="done",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        )

        # Step 2: 联网搜索补充
        t1 = time.monotonic()
        web_results = await self.web_search.execute(WebSearchInput(query=topic))
        steps.append(
            AgentStep(
                step_number=2,
                tool_name="web_search",
                input=topic,
                output=f"找到 {len(web_results.results)} 条网络结果",
                status="done",
                duration_ms=(time.monotonic() - t1) * 1000,
            )
        )

        # Step 3: 整合所有内容生成摘要
        t2 = time.monotonic()
        all_content_parts: list[str] = []
        for chunk in doc_results.chunks:
            all_content_parts.append(str(chunk.get("content", "")))
        for r in web_results.results:
            all_content_parts.append(r.get("snippet", ""))

        combined = "\n\n".join(all_content_parts[:5])  # 限制长度
        if combined:
            summary_result = await self.doc_summary.execute(
                DocSummaryInput(content=combined)
            )
            output = f"## 深度研究报告：{topic}\n\n### 摘要\n{summary_result.summary}\n\n### 关键要点\n"
            for i, point in enumerate(summary_result.key_points, 1):
                output += f"{i}. {point}\n"
        else:
            output = f"## 深度研究报告：{topic}\n\n未找到相关信息。请尝试上传相关文档或调整搜索关键词。"

        steps.append(
            AgentStep(
                step_number=3,
                tool_name="doc_summary",
                input=f"整合 {len(all_content_parts)} 条信息",
                output=output[:200],
                status="done",
                duration_ms=(time.monotonic() - t2) * 1000,
            )
        )

        total_ms = (time.monotonic() - t0) * 1000
        logger.info("deep_research_completed", topic=topic, step_count=len(steps), total_ms=round(total_ms))

        return SkillResult(
            output=output,
            steps=steps,
            data={
                "topic": topic,
                "doc_sources": len(doc_results.chunks),
                "web_sources": len(web_results.results),
            },
        )
