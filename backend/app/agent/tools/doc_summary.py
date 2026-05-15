"""
===============================================================================
文件名称: doc_summary.py
所属模块: app.agent.tools (Agent 工具模块)
项目角色: 实现"文档摘要"工具 —— 使用 LLM 对文档内容生成结构化摘要。

这个工具是 Agent 处理长文档的关键环节。当用户上传的文档内容很长时，
Agent 会调用本工具让 LLM 对内容进行压缩提炼，生成简洁的摘要和关键要点。
这有助于在后续处理中节省 token 成本，同时让 LLM 能更高效地理解文档核心内容。

工作流程：
  文档内容  -->  doc_summary 工具  -->  调用 LLM (ChatOpenAI) 生成摘要
  -->  解析 LLM 返回的文本  -->  提取摘要 + 关键要点  -->  返回结构化结果

错误处理：
  - 如果 LLM API Key 未配置，返回友好的错误提示（降级处理）
  - 如果 LLM 调用失败（网络问题、API 错误等），捕获异常并返回错误信息

关键概念：
  - ChatOpenAI: LangChain 提供的 OpenAI 兼容 LLM 客户端，可以对接任何
    兼容 OpenAI API 格式的服务（如本地模型、第三方 API 等）
  - temperature: 控制 LLM 生成文本的"创造性/随机性"。
    0.0 = 完全确定性（同样的输入总是产生同样的输出）
    1.0 = 最大随机性。摘要任务用 0.2 以获得较稳定的结果。
  - langchain_openai: LangChain 生态中专门用于 OpenAI 模型的集成包
===============================================================================
"""

# ---------------------------------------------------------------------------
# (1) 导入区
# ---------------------------------------------------------------------------

# 延迟类型注解求值，让类型引用更灵活
from __future__ import annotations

# Field: Pydantic 的字段描述函数，用于给模型字段添加元信息
from pydantic import Field

# 从工具基类导入三个核心基类
from app.agent.tools.base import BaseTool, ToolInput, ToolOutput
# get_settings: 获取应用配置（通过依赖注入或环境变量），包含 LLM 相关配置
from app.config import get_settings
# logger: 结构化日志记录器，用于记录工具的运行状态、警告和错误
from app.core.logging import logger


# ---------------------------------------------------------------------------
# (2) DocSummaryInput - 文档摘要的入参定义
# ---------------------------------------------------------------------------

class DocSummaryInput(ToolInput):
    """
    文档摘要工具的输入参数。

    字段说明：
        content (str): 需要进行摘要的文档全文内容。
                       注意：如果内容过长（>4000 字符），execute() 内部会自动截断。
    """
    content: str = Field(..., description="需要总结的文档内容")


# ---------------------------------------------------------------------------
# (3) DocSummaryOutput - 文档摘要的出参定义
# ---------------------------------------------------------------------------

class DocSummaryOutput(ToolOutput):
    """
    文档摘要工具的输出结果。

    字段说明：
        summary (str): 2-3 句话的文档核心内容摘要
        key_points (list[str]): 3-5 个关键要点的列表
    """
    # 摘要文本，通常 2-3 句话
    summary: str
    # 关键要点列表，每个元素是一句话
    key_points: list[str]


# ---------------------------------------------------------------------------
# (4) DocSummaryTool - 文档摘要工具的具体实现
# ---------------------------------------------------------------------------

class DocSummaryTool(BaseTool):
    """
    文档摘要工具。

    调用 LLM（大语言模型）对指定的文档内容生成结构化摘要和关键要点。

    继承自 BaseTool，必须实现 execute() 方法。
    """

    # 工具名称，Agent 通过此名称调度工具
    name = "doc_summary"
    # 工具描述，LLM 阅读此描述来决定何时调用该工具
    description = (
        "对指定的文档内容生成结构化摘要和关键要点。"
        "当用户需要总结或概括某篇文档的内容时使用此工具。"
        "输入：content（文档文本内容）"
        "输出：summary（摘要文本）、key_points（关键要点列表）"
    )

    async def execute(self, params: DocSummaryInput) -> DocSummaryOutput:
        """
        执行文档摘要生成（异步方法）。

        执行流程：
            1. 获取应用配置，检查 LLM API Key 是否已配置
            2. 如果未配置 API Key，返回降级提示（不调用 LLM）
            3. 初始化 ChatOpenAI LLM 客户端
            4. 构建摘要提示词（prompt），内容截断至 4000 字符
            5. 调用 LLM 生成摘要
            6. 解析 LLM 返回的文本，提取摘要和关键要点
            7. 如果任何步骤失败，捕获异常并返回错误信息

        参数：
            params (DocSummaryInput): 包含 content 字段的输入对象

        返回：
            DocSummaryOutput: 包含 summary 和 key_points 的输出对象
        """
        # 获取应用配置对象。
        # get_settings() 是一个 FastAPI 风格的依赖注入函数，
        # 它从环境变量或配置文件读取设置，返回一个 Settings 实例。
        settings = get_settings()

        # ------------------------------------------------------------------
        # (a) 检查 LLM API Key 是否已配置 —— 降级处理
        # ------------------------------------------------------------------
        # if not settings.llm_api_key: 判断 API Key 是否为空或未配置
        if not settings.llm_api_key:
            # logger.warning: 记录一条警告日志，标签为 "doc_summary_no_api_key"
            # 这有助于运维人员排查问题：搜索日志中的 "doc_summary_no_api_key"
            # 就能找到所有因为缺少 API Key 而无法执行摘要的情况
            logger.warning("doc_summary_no_api_key")

            # 返回降级结果：不调用 LLM，只返回内容长度信息。
            # f"...{len(params.content)} 字符": f-string 格式化字符串，
            #   {len(params.content)} 会在运行时被替换为内容的实际字符数。
            return DocSummaryOutput(
                summary=f"（无法生成摘要——未配置 API Key）\n内容长度: {len(params.content)} 字符",
                key_points=["请配置 LLM API Key 后重试"],
            )

        # ------------------------------------------------------------------
        # (b) 正常流程：调用 LLM 生成摘要
        # ------------------------------------------------------------------
        # try 块：包裹可能抛出异常的代码。
        # 如果在 LLM 调用过程中出现任何异常（网络错误、API 错误、JSON 解析错误），
        # 都会被 except 块捕获，而不是让异常传播到上层导致 Agent 崩溃。
        try:
            # from langchain_openai import ChatOpenAI: 延迟导入（lazy import）。
            # 为什么要在这个位置导入而不是文件顶部？
            # 1. 只在实际需要时加载，未配置 API Key 时不需要加载这个依赖
            # 2. 避免启动时就因为缺少 langchain_openai 包而崩溃
            # 3. 减少模块的初始化时间
            from langchain_openai import ChatOpenAI

            # 创建 ChatOpenAI LLM 客户端实例。
            # 各参数说明：
            #   model: 使用的模型名称（如 "gpt-4o", "gpt-3.5-turbo"），
            #          从配置文件/环境变量读取
            #   api_key: OpenAI 兼容的 API 密钥
            #   base_url: API 端点 URL，用于对接非 OpenAI 的第三方服务
            #            （如阿里百炼、本地 Ollama 等兼容接口）
            #   temperature=0.2: 控制生成文本的随机性。
            #        0.2 比较低，意味着输出较确定，适合摘要这种需要准确性的任务
            llm = ChatOpenAI(
                model=settings.llm_model,
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
                temperature=0.2,
            )

            # 构建提示词（prompt）。
            # f"...{params.content[:4000]}": 截取 content 的前 4000 个字符。
            # 为什么要截断？
            #   - LLM 有上下文窗口限制（如 4096 tokens）
            #   - 太长的输入会增加成本和延迟
            #   - 4000 字符对大多数文档已足够提取核心信息
            prompt = (
                "请对以下文档内容生成摘要，要求：\n"
                "1. 用 2-3 句话概括核心内容\n"
                "2. 列出 3-5 个关键要点\n\n"
                f"## 文档内容\n{params.content[:4000]}"
            )

            # await llm.ainvoke(prompt): 异步调用 LLM。
            # ainvoke 是 LangChain 提供的异步调用方法（a 前缀表示 async）。
            # 传入 prompt 字符串，LLM 会生成回复文本。
            response = await llm.ainvoke(prompt)

            # 从 LLM 响应中提取文本内容。
            # hasattr(response, "content"): 检查 response 对象是否有 content 属性。
            #   如果有（如 AIMessage 对象），用 response.content
            #   否则用 str(response) 将其转为字符串
            # 这种写法使代码兼容不同类型的 LLM 响应格式。
            text = response.content if hasattr(response, "content") else str(response)

            # ------------------------------------------------------------------
            # (c) 解析 LLM 返回的文本 —— 简单解析策略
            # ------------------------------------------------------------------
            # text.strip().split("\n"): 去除首尾空白后按换行符分割成多行
            lines = text.strip().split("\n")

            # 第一行作为摘要（如果列表为空则用原始文本兜底）
            # 语法: value_if_true if condition else value_if_false
            summary = lines[0] if lines else text

            # 从第二行开始提取关键要点：
            #   lines[1:]   -- 跳过第一行（摘要），取第 2 行及之后的所有行
            #   if l.strip() -- 过滤掉空行（strip() 后为空的行会被跳过）
            #   l.strip("- ")  -- 去除每行开头的 "- " 或 " " 前缀
            #   [:5]         -- 最多取 5 个要点
            key_points = [l.strip("- ") for l in lines[1:] if l.strip()][:5]

            # 返回成功生成的摘要结果
            return DocSummaryOutput(summary=summary, key_points=key_points)

        except Exception as e:
            # ------------------------------------------------------------------
            # (d) 异常处理：LLM 调用失败时的兜底策略
            # ------------------------------------------------------------------
            # logger.error: 记录错误日志，包含错误信息。
            #   error=str(e): 将异常对象转为字符串以便记录
            #   标签 "doc_summary_failed" 方便日志检索
            logger.error("doc_summary_failed", error=str(e))

            # 返回错误信息：告诉用户摘要生成失败了。
            # 这样即使 LLM 不可用，Agent 仍然可以正常工作（优雅降级），
            # 而不是直接崩溃。
            return DocSummaryOutput(
                summary=f"摘要生成失败: {e}",
                key_points=[],
            )
