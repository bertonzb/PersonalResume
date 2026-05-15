"""
Agent 主编排器 (Orchestrator)
===============================
本文件实现了 AI Agent 的核心调度逻辑，负责：
1. 创建和配置大语言模型 (LLM)
2. 将工具 (Tools) 注册给 Agent 使用
3. 执行用户请求并解析 Agent 返回的步骤与回复

关键概念：
---------
- Agent (智能体)：能够自主选择工具、分步骤完成任务的 AI 程序
- 编排 (Orchestration)：将多个工具、LLM 调用串联起来形成工作流
- 工具调用 (Tool Calling)：Agent 在推理过程中调用外部函数（如搜索、读文件）
"""

from __future__ import annotations  # 允许在类型注解中使用类名本身（前向引用），如 AgentStep 引用自身

import uuid
from dataclasses import dataclass, field  # @dataclass 装饰器，见下方 DataClass 注释
from typing import Any

# ---- LangChain 核心导入 ----
# LangChain 是构建 LLM 应用的流行框架，提供了 Agents、Tools、Chains 等抽象
from langchain.agents import create_agent  # 创建 Agent 的工厂函数
from langchain_core.tools import StructuredTool  # 结构化工具基类，支持 Pydantic 参数校验
# LLM 实例通过 LLMProvider 统一创建

# 项目中自定义的本地工具
from app.agent.tools.doc_retrieval import DocRetrievalInput, DocRetrievalTool
from app.agent.tools.doc_summary import DocSummaryInput, DocSummaryTool
from app.agent.tools.web_search import WebSearchInput, WebSearchTool
# MCP 客户端 —— Agent 通过 MCP 协议调用工具
from app.agent.mcp.client import MCPClient
from app.core.llm_provider import LLMProvider
from app.core.logging import logger

# MCP 工具的输入参数模型（读写文件只需要路径和内容两个字段）
from pydantic import BaseModel, Field


class MCPToolInput(BaseModel):
    """MCP 工具通用输入——工具名 + 参数。"""
    tool_name: str = Field(..., description="要调用的 MCP 工具名称：read_file / write_file / query_weather")
    path: str = Field("", description="文件路径（read_file / write_file 使用）")
    content: str = Field("", description="写入内容（write_file 使用）")
    city: str = Field("", description="城市名称（query_weather 使用，如'北京'、'上海'）")


# ============================================================================
# DataClass 详解
# ============================================================================
# @dataclass 是 Python 3.7+ 提供的装饰器。
# 作用：自动为你生成 __init__、__repr__、__eq__ 等方法，减少样板代码。
# 对比普通类，你只需要定义属性名和类型，不需要手写 __init__。
# 示例：
#   step = AgentStep(step_number=1, tool_name="search", ...)  # 自动生成的构造器
#   print(step)  # 自动生成的 __repr__，方便调试

@dataclass
class AgentStep:
    """
    Agent 执行过程中的单步记录。

    当 Agent 调用一个工具时，会产生一条 AgentStep 记录，
    用于前端展示执行过程和追踪日志。

    字段说明：
    --------
    step_number : int
        步骤序号（从 1 开始递增）
    tool_name : str
        被调用的工具名称，如 "web_search"、"doc_retrieval"
    input : str
        传给工具的输入参数（截取前 200 字符用于展示）
    output : str
        工具返回的结果（当前版本暂未填充）
    status : str
        步骤状态：
        - "thinking"  : Agent 正在思考下一步做什么
        - "acting"    : Agent 正在执行工具调用
        - "observing" : Agent 正在观察工具返回结果
        - "done"      : 步骤已完成
        - "error"     : 步骤出错
    duration_ms : float
        该步骤耗时（毫秒）
    """
    step_number: int
    tool_name: str
    input: str
    output: str
    status: str  # thinking | acting | observing | done | error
    duration_ms: float


@dataclass
class AgentResult:
    """
    Agent 执行完成后的最终结果。

    这是 Agent 编排器返回给上层的统一数据结构，
    包含 AI 的回复、执行步骤和追踪信息。

    字段说明：
    --------
    reply : str
        AI 的最终文本回复（中文）
    steps : list[AgentStep]
        执行过程中所有的工具调用步骤
    sources : list[dict]
        引用的数据来源列表（如文档标题、URL 等）
    trace_id : str
        本次执行的唯一追踪 ID（UUID），用于关联日志
    """
    reply: str
    steps: list[AgentStep]
    sources: list[dict[str, Any]]
    trace_id: str


# ============================================================================
# AgentOrchestrator --- 主编排器
# ============================================================================

class AgentOrchestrator:
    """
    Agent 主编排器，负责管理 LLM、工具和各种推理步骤。

    工作流程概览：
    1. 初始化时创建 LLM 实例和工具列表
    2. 构建 system_prompt（系统提示词），告诉 Agent 它的角色和行为规则
    3. 调用 create_agent(...) 创建一个能使用工具的 LangChain Agent
    4. 用户发消息时，调用 agent.ainvoke() 执行异步推理
    5. 解析返回的消息列表，提取 AI 回复和工具调用步骤
    """

    def __init__(self) -> None:
        # ---- 创建 LLM（通过 LLMProvider 统一管理，支持 API/vLLM/SGLang 切换）----
        self.llm = LLMProvider.create()

        # ---- MCP 客户端 ----
        # 连接本地 MCP Server，Agent 可以通过 MCP 协议读写文件
        self.mcp_client = MCPClient()

        # ---- 构建工具列表 ----
        # 将本地工具 + MCP 工具一起包装成 LangChain 能识别的 StructuredTool 对象
        self.tools = self._build_tools()

        # ---- 创建 Agent ----
        # create_agent 是 create_agent() 函数（LangChain 1.x 推荐 API），
        # 它将 LLM + Tools + system_prompt 组合成一个完整的 Agent。
        self._agent = self._create_agent()

    def _build_tools(self) -> list[StructuredTool]:
        """
        将本地定义的 Tool 对象转换为 LangChain 能用的 StructuredTool 列表。

        每个工具需要提供：
        - name         : 工具名称，Agent 用它来识别和调用工具
        - description  : 工具说明，帮助 Agent 理解何时使用这个工具
        - args_schema  : Pydantic 模型，定义工具的输入参数格式（自动校验）
        - coroutine    : 实际执行逻辑的异步函数

        StructuredTool.from_function 详解
        ------------------------------------
        这是 LangChain 提供的工厂方法，用于将普通函数包装成 Tool 对象。
        参数说明：
        - func=None: 同步函数。这里设为 None，因为我们提供异步版本。
        - coroutine=: 异步函数（即 async def），LangChain 会用它来执行工具。
                      当 Agent 决定调用某个工具时，LangChain 会 await 这个协程。
        """
        # 实例化三个本地工具
        doc_retrieval = DocRetrievalTool()  # 文档检索工具
        doc_summary = DocSummaryTool()      # 文档摘要工具
        web_search = WebSearchTool()        # 网络搜索工具

        # ---- MCP 工具包装 ----
        # 定义一个异步函数，将 Agent 的调用转发给 MCP Client
        async def _mcp_run(**kwargs):
            parsed = MCPToolInput(**kwargs)
            # 根据工具名构建对应的参数
            args = {}
            if parsed.tool_name == "query_weather":
                args = {"city": parsed.city}
            elif parsed.tool_name == "write_file":
                args = {"path": parsed.path, "content": parsed.content}
            else:  # read_file 及其他
                args = {"path": parsed.path}
            result = await self.mcp_client.call_tool(parsed.tool_name, args)
            return result

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
            # ---- 第 4 个工具：MCP 文件操作 ----
            StructuredTool.from_function(
                name="mcp_filesystem",
                description=(
                    "通过 MCP 协议操作文件和查询信息。支持以下子工具：\n"
                    "- read_file: 读取工作区文件内容 → 参数 tool_name='read_file', path=文件路径\n"
                    "- write_file: 将内容写入文件 → 参数 tool_name='write_file', path=文件路径, content=写入内容\n"
                    "- query_weather: 查询城市天气 → 参数 tool_name='query_weather', city=城市名(如'北京')\n"
                ),
                args_schema=MCPToolInput,
                func=None,
                coroutine=_mcp_run,
            ),
        ]

    def _wrap_tool(self, tool: Any):
        """
        将本地 Tool 包装为一个标准的异步函数（闭包模式）。

        闭包 (Closure) 模式详解：
        -----------------------
        注意这里定义了一个内部函数 _run，并且 _run 引用了外层函数的参数 tool。
        _wrap_tool 返回的是 _run 这个函数对象本身（不是调用结果）。

        当一个函数能记住它被创建时的环境变量（这里是 tool），
        这就叫"闭包"——函数"闭合"了它外部的变量。

        为什么需要这样做？
        - StructuredTool.from_function 要求传入一个标准的 async def 函数
        - 但我们每个 tool 对象不同（doc_retrieval、doc_summary、web_search）
        - 通过闭包，我们为每个 tool 创建了专属的 _run 函数
        - 当 _run 被调用时，tool 始终指向正确的工具对象

        参数传递流程：
        kwargs (Agent 传入的参数字典) → tool.execute(input_schema) → JSON 字符串
        """
        # 定义内部异步函数。**kwargs 收集所有关键字参数为一个字典。
        async def _run(**kwargs):
            # kwargs 就是工具的输入参数，如 {"query": "什么是RAG", "top_k": 5}
            input_schema = kwargs
            # 调用工具的实际执行逻辑（异步）
            result = await tool.execute(input_schema)
            # 工具返回的是一个 Pydantic 对象，转为 JSON 字符串给 LangChain
            return result.model_dump_json()

        # 注意：这里返回的是函数对象 _run，而不是 _run() 的调用结果！
        return _run

    def _create_agent(self):
        """
        创建 LangChain Agent 实例。

        system_prompt（系统提示词）详解：
        --------------------------------
        系统提示词是发给 LLM 的第一条消息，相当于给 AI 设定"人设"和"规则"。
        - 它不会被用户看到，但会固定出现在每次 LLM 调用的最前面
        - 它告诉 Agent：你是谁、你能做什么、你应该如何思考
        - 好的 system_prompt 需要清晰列举可用工具和使用规则

        本项目的 system_prompt 采用中文，指导 Agent：
        1. 先判断问题类型
        2. 优先检索知识库，必要时搜索互联网
        3. 多步骤任务依次调用多个工具
        4. 最后整合信息给出结构化回答
        """
        system_prompt = (
            "你是一个个人知识库深度研究助手 DeepScribe。你可以使用以下工具：\n"
            "- doc_retrieval: 在用户的知识库中检索文档\n"
            "- web_search: 搜索互联网获取最新信息\n"
            "- doc_summary: 生成文档摘要和关键要点\n"
            "- mcp_filesystem: 通过 MCP 协议操作文件或查询信息（read_file/write_file/query_weather）\n\n"
            "当用户提出问题时：\n"
            "1. 先判断问题类型，选择合适的工具\n"
            "2. 如果问题与用户的知识库相关，优先使用 doc_retrieval\n"
            "3. 如果需要最新信息或知识库中无相关内容，使用 web_search\n"
            "4. 如果用户查询天气，使用 mcp_filesystem(tool_name='query_weather', city='城市名')\n"
            "5. 如果用户要求保存报告，使用 mcp_filesystem(tool_name='write_file', ...)\n"
            "6. 对于多步骤的研究任务，依次调用多个工具\n"
            "7. 最后整合所有信息，给出结构化的回答\n\n"
            "请用中文回答。如果使用工具，请说明你使用了哪些工具。"
        )

        # create_agent() 是 LangChain 1.x 的推荐 API
        # 它内部使用 create_agent 模式，将 LLM、工具列表、系统提示词绑定在一起
        # 返回的 agent 对象可以通过 ainvoke() 调用
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
        """
        执行 Agent 任务，这是外部调用 Agent 的主入口。

        参数说明：
        ----------
        user_id : uuid.UUID | None
            用户 ID，用于追踪和个性化（当前版本为可选项）
        message : str
            用户输入的消息文本
        conversation_id : uuid.UUID | None
            会话 ID，用于支持多轮对话（当前版本为可选项）

        返回：
        ------
        AgentResult : 包含 AI 回复、执行步骤、来源和追踪 ID

        执行流程详解：
        -------------
        1. 生成 trace_id 用于全链路日志追踪
        2. 调用 agent.ainvoke() 执行异步推理（ainvoke = async invoke）
        3. 解析返回的 messages 列表，提取 AI 最终回复
        4. 遍历 messages 中的 tool_calls，生成 AgentStep 记录
        5. 如果出错，捕获异常并返回错误信息
        """
        import time
        import json

        trace_id = str(uuid.uuid4())
        steps: list[AgentStep] = []

        logger.info(
            "agent_run_started",
            trace_id=trace_id,
            user_id=str(user_id) if user_id else None,
            message_length=len(message),
        )

        # ---- 预判处理：天气查询（DeepSeek 工具调用不稳定，这里直接查）----
        weather_kw = ["天气", "气温", "下雨", "下雪", "温度", "湿度", "刮风",
                      "雾霾", "台风", "空气质量", "几度", "多少度"]
        if any(kw in message for kw in weather_kw):
            cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京",
                      "西安", "重庆", "天津", "苏州", "长沙", "郑州", "青岛", "沈阳",
                      "宁波", "昆明", "大连", "厦门", "合肥", "福州", "哈尔滨", "济南"]
            found = None
            for c in cities:
                if c in message:
                    found = c
                    break
            if found:
                try:
                    t1 = time.monotonic()
                    raw = await self.mcp_client.call_tool("query_weather", {"city": found})
                    wd = json.loads(raw) if isinstance(raw, str) else raw
                    if "error" not in wd:
                        weather_reply = (
                            f"{found}当前天气：{wd.get('weather','')}，"
                            f"温度{wd.get('temperature','')}，体感{wd.get('feels_like','')}，"
                            f"湿度{wd.get('humidity','')}，风速{wd.get('wind_speed','')}，"
                            f"能见度{wd.get('visibility','')}。"
                        )
                        steps.append(AgentStep(step_number=1,
                            tool_name="MCP:query_weather", input=f"city={found}",
                            output=json.dumps(wd, ensure_ascii=False)[:200],
                            status="done", duration_ms=(time.monotonic()-t1)*1000))
                        return AgentResult(
                            reply=weather_reply,
                            steps=steps,
                            sources=[],
                            trace_id=trace_id,
                        )
                except Exception as e:
                    logger.error("weather_precheck_failed", error=str(e))

        t0 = time.monotonic()
        # ---- 非天气问题：走 RAG 管道（已验证有效）----
        from app.services.chat_service import ChatService
        chat_svc = ChatService()
        chat_result = await chat_svc.process_message(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        duration_ms = (time.monotonic() - t0) * 1000
        logger.info("agent_run_completed", trace_id=trace_id, step_count=0, total_duration_ms=round(duration_ms))
        return AgentResult(
            reply=chat_result.reply,
            steps=steps,
            sources=[{"chunk_id": s.chunk_id, "content": s.content, "score": s.score} for s in chat_result.sources],
            trace_id=trace_id,
        )
