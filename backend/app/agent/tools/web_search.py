from __future__ import annotations

import json

from pydantic import Field

from app.agent.tools.base import BaseTool, ToolInput, ToolOutput
from app.config import get_settings
from app.core.logging import logger


class WebSearchInput(ToolInput):
    query: str = Field(..., description="搜索关键词")


class WebSearchOutput(ToolOutput):
    results: list[dict[str, str]]


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "在互联网上搜索最新的信息。"
        "当用户的问题涉及实时信息、最新新闻，或知识库中没有相关内容时使用此工具。"
        "输入：query（搜索关键词）"
        "输出：results（搜索结果列表，每项包含 title、url、snippet）"
    )

    async def execute(self, params: WebSearchInput) -> WebSearchOutput:
        settings = get_settings()

        if not settings.tavily_api_key:
            logger.warning("web_search_no_api_key")

            # 降级: 返回模拟结果
            return WebSearchOutput(
                results=[
                    {
                        "title": f"关于「{params.query}」的搜索结果",
                        "url": "https://example.com",
                        "snippet": "请配置 TAVILY_API_KEY 以启用真实搜索功能。当前为降级模式。",
                    }
                ]
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": params.query,
                        "max_results": 5,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()

            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", ""),
                }
                for r in data.get("results", [])
            ]

            logger.info("web_search_completed", query=params.query, result_count=len(results))
            return WebSearchOutput(results=results)

        except Exception as e:
            logger.error("web_search_failed", error=str(e), query=params.query)
            return WebSearchOutput(
                results=[
                    {
                        "title": "搜索失败",
                        "url": "",
                        "snippet": f"搜索服务暂时不可用: {e}",
                    }
                ]
            )
