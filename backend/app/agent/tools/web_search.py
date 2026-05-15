"""
===============================================================================
文件名称: web_search.py
所属模块: app.agent.tools (Agent 工具模块)
项目角色: 实现"网络搜索"工具 —— 在互联网上搜索最新信息。

这个工具让 Agent 具备获取实时信息的能力。当用户的提问需要最新数据
（如新闻、实时股价、最新政策），而知识库中没有相关内容时，
Agent 会调用本工具发起网络搜索。

底层使用 Tavily Search API（专为 AI Agent 优化的搜索引擎），
返回结构化的搜索结果（标题、URL、摘要）。

工作流程：
  用户提问  -->  Agent 判断需要网络搜索  -->  调用 Tavily API
  -->  解析搜索结果  -->  返回标题+URL+摘要列表

错误处理：
  - 如果 Tavily API Key 未配置，返回降级提示（模拟结果）
  - 如果 API 调用失败（网络超时、API 错误），捕获异常并返回错误信息

关键概念：
  - httpx.AsyncClient: 一个现代的 Python 异步 HTTP 客户端库。
    类似于 requests 库，但支持 async/await 异步编程模式。
  - async with: Python 异步上下文管理器语法。进入时创建连接池，
    退出时自动关闭所有连接。确保资源正确释放，避免连接泄漏。
  - timeout: 请求超时时间。如果服务器在指定时间内未响应，抛出超时异常。
  - Tavily: 专为 AI Agent 设计的搜索 API。不同于 Google/Bing 等通用搜索，
    Tavily 返回的结果经过 AI 优化，更适合 LLM 消费。
===============================================================================
"""

# ---------------------------------------------------------------------------
# (1) 导入区
# ---------------------------------------------------------------------------

# 延迟类型注解求值
from __future__ import annotations

# json: Python 标准库的 JSON 处理模块。虽然当前代码中未显式使用 json 函数，
# 但保留此导入为将来可能的 JSON 操作做准备（如手动解析、格式化输出等）。
import json

# Field: Pydantic 的字段描述函数
from pydantic import Field

# 从工具基类导入核心基类
from app.agent.tools.base import BaseTool, ToolInput, ToolOutput
# 获取应用配置（包含 tavily_api_key）
from app.config import get_settings
# 结构化日志记录器
from app.core.logging import logger


# ---------------------------------------------------------------------------
# (2) WebSearchInput - 网络搜索的入参定义
# ---------------------------------------------------------------------------

class WebSearchInput(ToolInput):
    """
    网络搜索工具的输入参数。

    字段说明：
        query (str): 用户想要搜索的关键词。
                     例如 "2025年诺贝尔和平奖得主"
    """
    query: str = Field(..., description="搜索关键词")


# ---------------------------------------------------------------------------
# (3) WebSearchOutput - 网络搜索的出参定义
# ---------------------------------------------------------------------------

class WebSearchOutput(ToolOutput):
    """
    网络搜索工具的输出结果。

    字段说明：
        results (list[dict[str, str]]): 搜索结果列表。
            每个结果是一个字典，包含三个键：
              - "title" (str): 搜索结果的标题
              - "url" (str): 搜索结果的链接地址
              - "snippet" (str): 搜索结果的摘要/片段文本
    """
    results: list[dict[str, str]]


# ---------------------------------------------------------------------------
# (4) WebSearchTool - 网络搜索工具的具体实现
# ---------------------------------------------------------------------------

class WebSearchTool(BaseTool):
    """
    网络搜索工具。

    通过 Tavily Search API 在互联网上进行实时搜索，
    返回结构化的搜索结果。

    继承自 BaseTool，必须实现 execute() 方法。
    """

    # 工具名称
    name = "web_search"
    # 工具描述：LLM 通过阅读此描述来决定是否调用网络搜索
    description = (
        "在互联网上搜索最新的信息。"
        "当用户的问题涉及实时信息、最新新闻，或知识库中没有相关内容时使用此工具。"
        "输入：query（搜索关键词）"
        "输出：results（搜索结果列表，每项包含 title、url、snippet）"
    )

    async def execute(self, params: WebSearchInput) -> WebSearchOutput:
        """
        执行网络搜索（异步方法）。

        执行流程：
            1. 获取应用配置，检查 Tavily API Key
            2. 如果未配置 API Key，返回模拟结果（降级处理）
            3. 创建 httpx.AsyncClient 异步 HTTP 客户端
            4. 向 Tavily API 发送 POST 请求
            5. 解析响应 JSON，提取搜索结果
            6. 记录成功日志
            7. 如果任何步骤失败，捕获异常并返回错误信息

        参数：
            params (WebSearchInput): 包含 query 字段的输入对象

        返回：
            WebSearchOutput: 包含 results 列表的输出对象
        """
        # 获取应用配置
        settings = get_settings()

        # ------------------------------------------------------------------
        # (a) 检查 Tavily API Key —— 降级处理
        # ------------------------------------------------------------------
        if not settings.tavily_api_key:
            # 记录警告日志，标签方便后续检索
            logger.warning("web_search_no_api_key")

            # 降级：返回模拟的搜索结果。
            # 这样做的好处是：
            #   1. 不会因为缺少 API Key 而崩溃
            #   2. 返回的模拟结果中包含了配置提示，引导用户正确配置
            #   3. Agent 流程仍然可以完整执行（对用户体验更好）
            return WebSearchOutput(
                results=[
                    {
                        "title": f"关于「{params.query}」的搜索结果",
                        "url": "https://example.com",
                        "snippet": "请配置 TAVILY_API_KEY 以启用真实搜索功能。当前为降级模式。",
                    }
                ]
            )

        # ------------------------------------------------------------------
        # (b) 正常流程：调用 Tavily API 进行搜索
        # ------------------------------------------------------------------
        try:
            # import httpx: 延迟导入 httpx 库。
            # 只在真正需要发起 HTTP 请求时才导入，
            # 避免在 API Key 未配置的非正常流程中也加载该库。
            import httpx

            # async with httpx.AsyncClient() as client:
            #   异步上下文管理器：创建一个异步 HTTP 客户端实例。
            #
            #   httpx.AsyncClient():
            #     - 管理 TCP 连接池（复用连接以提高效率）
            #     - 支持 HTTP/1.1 和 HTTP/2
            #     - 支持异步请求（不会阻塞事件循环）
            #
            #   async with:
            #     - __aenter__: 进入时初始化连接池
            #     - __aexit__: 退出时自动关闭所有连接、释放资源
            #     - 即使发生异常，也能确保资源被正确释放
            async with httpx.AsyncClient() as client:
                # await client.post(...): 发送异步 POST 请求到 Tavily API
                #   - 第一个参数是 URL
                #   - json={...}: 请求体为 JSON 格式，httpx 会自动设置 Content-Type
                #   - timeout=15.0: 超时时间 15 秒。如果 Tavily 在 15 秒内
                #     未响应，则抛出 httpx.TimeoutException
                response = await client.post(
                    "https://api.tavily.com/search",     # Tavily 搜索 API 端点
                    json={
                        "api_key": settings.tavily_api_key,  # API 密钥
                        "query": params.query,               # 搜索关键词
                        "max_results": 5,                    # 最多返回 5 条结果
                    },
                    timeout=15.0,  # 15 秒超时
                )

                # response.raise_for_status(): 检查 HTTP 状态码。
                # 如果状态码是 4xx 或 5xx（客户端错误或服务端错误），
                # 则抛出 httpx.HTTPStatusError 异常。
                # 例如：401 表示 API Key 无效，429 表示超出频率限制，
                # 500 表示服务端内部错误。
                response.raise_for_status()

                # response.json(): 将响应体的 JSON 内容解析为 Python 字典。
                # 假设响应格式为: {"results": [{"title": ..., "url": ..., "content": ...}, ...]}
                data = response.json()

            # ------------------------------------------------------------------
            # (c) 解析搜索结果
            # ------------------------------------------------------------------
            # 列表推导式：遍历 API 返回的结果列表，转换为统一的字典格式。
            #
            # data.get("results", []): 安全地从响应中取 results 字段。
            #   - 如果 results 存在，返回其值（列表）
            #   - 如果 results 不存在（API 返回了意外的格式），返回空列表 []
            #   - 使用 .get() 而非 data["results"] 可避免 KeyError
            #
            # r.get("title", ""): 从每条结果中安全地获取 title 字段。
            #   如果 title 不存在，返回空字符串 "" 作为默认值。
            #   同样适用于 url 和 content（映射为 snippet）。
            results = [
                {
                    "title": r.get("title", ""),     # 搜索结果标题
                    "url": r.get("url", ""),         # 搜索结果链接
                    "snippet": r.get("content", ""), # 搜索结果摘要（Tavily 用 content 字段）
                }
                for r in data.get("results", [])     # 遍历结果列表
            ]

            # 记录成功日志，包含搜索关键词和结果数量
            # result_count=len(results): 统计有多少条结果
            logger.info("web_search_completed", query=params.query, result_count=len(results))

            # 返回搜索结果
            return WebSearchOutput(results=results)

        except Exception as e:
            # ------------------------------------------------------------------
            # (d) 异常处理：API 调用失败时的兜底策略
            # ------------------------------------------------------------------
            # 可能触发的异常类型：
            #   - httpx.TimeoutException: 请求超时
            #   - httpx.HTTPStatusError: HTTP 状态码异常
            #   - httpx.ConnectError: 无法连接到服务器（DNS 失败、网络不通）
            #   - json.JSONDecodeError: 响应不是有效的 JSON
            #   - KeyError: API 响应格式不符合预期
            #
            # 所有异常都被统一捕获并处理，确保 Agent 不会因网络搜索失败而崩溃。

            # 记录错误日志，包含异常信息和搜索关键词
            logger.error("web_search_failed", error=str(e), query=params.query)

            # 返回错误信息：告诉用户搜索失败了，并附上具体错误原因。
            # 这种"优雅降级"策略确保 Agent 的稳健性。
            return WebSearchOutput(
                results=[
                    {
                        "title": "搜索失败",
                        "url": "",
                        "snippet": f"搜索服务暂时不可用: {e}",
                    }
                ]
            )
