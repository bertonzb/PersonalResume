"""
===============================================================================
文件名称: deep_research.py
所属模块: app.agent.skills (Agent 技能模块)
项目角色: 实现"深度研究"技能 —— 多源搜索 + 信息整合 + 研究报告生成。

这是整个 Agent 系统中最复杂的 Skill，展示了多个 Tool 的编排协作模式。
它演示了如何将原子工具（文档检索、网络搜索、摘要生成）组合成一个
完整的研究工作流。

工作流程（4 个阶段）：
  第 1 步：在用户知识库中搜索相关文档片段（doc_retrieval）
  第 2 步：在互联网上搜索补充信息（web_search）
  第 3 步：整合所有来源的内容，调用 LLM 生成结构化摘要（doc_summary）
  第 4 步：汇总所有步骤的执行记录，返回研究报告

时间测量：
  使用 time.monotonic() 而不是 time.time() 来测量耗时。
  原因：time.monotonic() 不受系统时间调整（如 NTP 校时、用户手动改时间）
  的影响，始终单调递增，适合测量时间间隔。

关键概念：
  - time.monotonic(): 返回一个单调递增的时钟值（单位：秒）。
    这个时钟不会被系统时间调整影响。两次调用的差值 = 精确的时间间隔。
    非常适合性能测量和超时判断。
  - context dict: 编排器传入的上下文字典，包含执行所需信息（如 topic）。
  - AgentStep: 每一步的记录对象，用于追踪执行过程和性能数据。
    * 1000 在耗时时：把秒转换为毫秒。time.monotonic() 返回秒，
      乘以 1000 得到毫秒。
===============================================================================
"""

# ---------------------------------------------------------------------------
# (1) 导入区
# ---------------------------------------------------------------------------

# 延迟类型注解求值
from __future__ import annotations

# time: Python 标准库的时间模块。
# time.monotonic(): 获取单调时钟的当前值（秒），用于精确测量时间间隔。
import time

# AgentStep: 编排器使用的步骤记录类。
# 每个 AgentStep 记录一次 Tool 调用的详细信息。
from app.agent.orchestrator import AgentStep

# 从 skills 基类导入 BaseSkill（Skill 抽象基类）和 SkillResult（结果数据类）
from app.agent.skills.base import BaseSkill, SkillResult

# 导入三个 Tool 及其输入类：
#   DocRetrievalTool / DocRetrievalInput：知识库文档检索
#   DocSummaryTool / DocSummaryInput： LLM 摘要生成
#   WebSearchTool / WebSearchInput：   互联网搜索
from app.agent.tools.doc_retrieval import DocRetrievalInput, DocRetrievalTool
from app.agent.tools.doc_summary import DocSummaryInput, DocSummaryTool
from app.agent.tools.web_search import WebSearchInput, WebSearchTool

# 结构化日志记录器
from app.core.logging import logger


# ---------------------------------------------------------------------------
# (2) DeepResearchSkill - 深度研究技能的具体实现
# ---------------------------------------------------------------------------

class DeepResearchSkill(BaseSkill):
    """
    深度研究 Skill。

    拆解研究问题，从多个来源（知识库 + 互联网）获取信息，
    使用 LLM 对比整合，最终输出结构化的研究报告。

    这个类展示了 Skill 的核心模式：在 execute() 中按步骤编排多个 Tool，
    每一步记录执行过程（AgentStep），最后汇总为 SkillResult。

    继承自 BaseSkill，必须实现 execute() 方法。
    """

    # 类属性文档字符串：描述 Skill 的核心功能
    """深度研究 Skill：拆解问题 → 多源搜索 → 对比整合 → 输出结构化提纲。"""

    # Skill 名称，供 Agent 识别和调度
    name = "deep_research"

    # Skill 描述，供 LLM 阅读以判断何时触发此 Skill
    description = (
        "对复杂的研究问题进行深度分析。流程包括：\n"
        "1. 拆解研究问题为多个子问题\n"
        "2. 对每个子问题在知识库和互联网中搜索\n"
        "3. 对比整合不同来源的信息\n"
        "4. 输出结构化的研究报告提纲\n"
        "当用户明确需要'深度研究'或'深入分析'某个主题时触发。"
    )

    def __init__(self) -> None:
        """
        初始化深度研究 Skill。

        在构造方法中创建所有需要的 Tool 实例。
        这些 Tool 实例作为实例属性，在整个 Skill 的生命周期中复用。

        为什么在 __init__ 中创建 Tool，而不是在 execute() 中创建？
          1. 复用：如果同一个 Skill 被多次调用，Tool 实例可以被复用
          2. 管理：集中管理依赖，方便测试时注入 mock Tool
          3. 效率：避免每次 execute 都重复创建和销毁 Tool 对象
        """
        # 实例化文档检索工具 —— 用于在用户知识库中搜索
        self.doc_retrieval = DocRetrievalTool()
        # 实例化网络搜索工具 —— 用于在互联网上搜索
        self.web_search = WebSearchTool()
        # 实例化文档摘要工具 —— 用于让 LLM 整合信息生成摘要
        self.doc_summary = DocSummaryTool()

    async def execute(self, context: dict) -> SkillResult:
        """
        执行深度研究（异步方法）。

        这是整个 Skill 的核心方法，按以下步骤执行：

        步骤 1: 从上下文中提取研究主题（topic）
        步骤 2: 在知识库中搜索相关文档
        步骤 3: 在互联网上搜索补充信息
        步骤 4: 整合所有来源内容，生成结构化摘要
        步骤 5: 汇总所有步骤记录，返回 SkillResult

        每一步都记录为 AgentStep，包含步骤编号、工具名称、
        输入输出、执行状态和耗时。

        参数：
            context (dict): 上下文字典，必须包含 "topic" 键。
                           例如: {"topic": "2025年AI行业发展趋势"}
                           也可以是空字典或缺少 topic 键，
                           此时会返回提示信息。

        返回：
            SkillResult: 包含输出文本、执行步骤和结构化数据的执行结果。
        """
        # ------------------------------------------------------------------
        # (a) 提取和验证研究主题
        # ------------------------------------------------------------------
        # context.get("topic", ""): 从上下文字典中安全地获取 "topic" 键的值。
        #   - 如果 "topic" 存在，返回其值
        #   - 如果 "topic" 不存在，返回默认值 ""（空字符串）
        topic = context.get("topic", "")

        # 验证主题是否为空。
        # if not topic: Python 中空字符串 "" 被视为假值（falsy）。
        # 如果没有提供研究主题，直接返回提示信息，不执行后续步骤。
        if not topic:
            # 快速返回：没有主题就无法研究，返回友好的错误提示。
            # steps=[]: 没有执行任何步骤，步骤列表为空。
            return SkillResult(output="请提供研究主题", steps=[])

        # ------------------------------------------------------------------
        # (b) 初始化步骤记录列表和时间基准
        # ------------------------------------------------------------------
        # steps: 存储每一步 AgentStep 记录的列表。
        # 类型注解 list[AgentStep] 帮助 IDE 和类型检查器提供更好的支持。
        steps: list[AgentStep] = []

        # t0 = time.monotonic(): 记录整个 Skill 的执行起始时间。
        # time.monotonic() 返回一个单调递增的浮点数（单位：秒）。
        # 为什么用 monotonic 而不是 time？
        #   - time.monotonic() 不受系统时间修改的影响（NTP 校时不会导致跳跃）
        #   - 它保证单调递增，两次调用的差值 = 精确的时间间隔
        #   - 专门为性能测量而设计
        # 后续通过 time.monotonic() - t0 可计算从开始到现在经过的秒数。
        t0 = time.monotonic()

        # 记录日志：深度研究已开始，包含研究主题
        logger.info("deep_research_started", topic=topic)

        # ------------------------------------------------------------------
        # 步骤 1: 在知识库中搜索相关文档
        # ------------------------------------------------------------------
        # await self.doc_retrieval.execute(DocRetrievalInput(query=topic)):
        #   调用文档检索工具，传入用户的研究主题作为查询文本。
        #   DocRetrievalInput(query=topic): 构造输入对象，Pydantic 会自动校验。
        #   await: 等待异步检索操作完成（可能与向量数据库交互）。
        doc_results = await self.doc_retrieval.execute(DocRetrievalInput(query=topic))

        # 记录第 1 步的执行信息为 AgentStep
        steps.append(
            AgentStep(
                step_number=1,                                    # 步骤编号：第 1 步
                tool_name="doc_retrieval",                        # 使用的工具名称
                input=topic,                                      # 输入：研究主题
                output=f"找到 {len(doc_results.chunks)} 个相关片段", # 输出：描述性文本
                status="done",                                    # 状态：执行完成
                # duration_ms: 计算从 t0 到现在的耗时（毫秒）。
                # (time.monotonic() - t0): 从开始到现在经过的秒数（浮点数）
                # * 1000: 将秒转换为毫秒
                # 例如: 0.523 * 1000 = 523 毫秒
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        )

        # ------------------------------------------------------------------
        # 步骤 2: 在互联网上搜索补充信息
        # ------------------------------------------------------------------
        # t1 = time.monotonic(): 记录第 2 步的起始时间。
        # 这里重新取了 monotonic() 的值，以便单独测量第 2 步的耗时。
        t1 = time.monotonic()

        # 调用网络搜索工具，同样以研究主题为查询关键词
        web_results = await self.web_search.execute(WebSearchInput(query=topic))

        # 记录第 2 步的执行信息
        steps.append(
            AgentStep(
                step_number=2,                                      # 步骤编号：第 2 步
                tool_name="web_search",                             # 使用的工具名称
                input=topic,                                        # 输入：研究主题
                output=f"找到 {len(web_results.results)} 条网络结果", # 输出：结果数量
                status="done",                                      # 状态：执行完成
                # (time.monotonic() - t1) * 1000: 第 2 步的耗时（毫秒）
                duration_ms=(time.monotonic() - t1) * 1000,
            )
        )

        # ------------------------------------------------------------------
        # 步骤 3: 整合所有来源的内容，生成结构化摘要
        # ------------------------------------------------------------------
        # t2 = time.monotonic(): 记录第 3 步的起始时间
        t2 = time.monotonic()

        # all_content_parts: 收集所有来源的文本内容片段。
        # 类型注解 list[str] 表示这是一个字符串列表。
        all_content_parts: list[str] = []

        # 遍历知识库检索结果，提取每个文档片段的内容文本。
        # doc_results.chunks 是步骤 1 返回的文档片段列表。
        # chunk.get("content", ""): 安全地获取 "content" 键的值。
        #   如果该键不存在，返回空字符串 ""，避免 KeyError。
        # str(...): 确保内容是字符串类型（因为 chunks 的类型是 dict[str, str | float]）。
        for chunk in doc_results.chunks:
            all_content_parts.append(str(chunk.get("content", "")))

        # 遍历网络搜索结果，提取每个结果的摘要文本。
        # r.get("snippet", ""): 从网络搜索结果中提取 snippet（摘要）字段。
        for r in web_results.results:
            all_content_parts.append(r.get("snippet", ""))

        # 将所有内容片段用两个换行符拼接为一个字符串。
        # "\n\n".join(...): 以两个换行符作为分隔符连接所有片段。
        # all_content_parts[:5]: 最多取前 5 个片段，限制总内容长度。
        # 为什么要限制长度？
        #   - LLM 的上下文窗口有限，输入过长会被截断
        #   - Token 成本：每多 1000 个 token 都会增加 API 费用
        #   - 前 5 个片段通常已包含最相关的信息
        combined = "\n\n".join(all_content_parts[:5])  # 限制长度

        # ------------------------------------------------------------------
        # (c) 分支处理：根据是否有内容来决定输出策略
        # ------------------------------------------------------------------
        if combined:
            # 有内容：调用 LLM 摘要工具生成结构化报告

            # 调用文档摘要工具，对整合后的内容生成摘要
            # await: 等待 LLM 生成摘要（可能需要几秒钟）
            summary_result = await self.doc_summary.execute(
                DocSummaryInput(content=combined)
            )

            # 构建 Markdown 格式的研究报告文本
            # f"## 深度研究报告：{topic}": 用 f-string 将研究主题嵌入 Markdown 标题
            output = f"## 深度研究报告：{topic}\n\n### 摘要\n{summary_result.summary}\n\n### 关键要点\n"

            # enumerate(summary_result.key_points, 1): 遍历关键要点列表。
            #   - enumerate 返回 (索引, 元素) 的元组
            #   - 第二个参数 1 表示索引从 1 开始（而不是默认的 0）
            #   - 例如: (1, "要点A"), (2, "要点B"), ...
            for i, point in enumerate(summary_result.key_points, 1):
                # 将每个要点格式化为编号列表项
                # f"{i}. {point}\n": 生成 "1. 要点内容\n" 格式
                output += f"{i}. {point}\n"
        else:
            # 无内容：知识库和网络搜索都没有找到相关信息
            # 返回友好的未找到提示
            output = f"## 深度研究报告：{topic}\n\n未找到相关信息。请尝试上传相关文档或调整搜索关键词。"

        # 记录第 3 步的执行信息
        steps.append(
            AgentStep(
                step_number=3,                                              # 步骤编号：第 3 步
                tool_name="doc_summary",                                    # 使用的工具名称
                input=f"整合 {len(all_content_parts)} 条信息",              # 输入描述
                output=output[:200],                                        # 输出前 200 字符（避免记录太长）
                status="done",                                              # 状态：执行完成
                duration_ms=(time.monotonic() - t2) * 1000,                # 第 3 步耗时（毫秒）
            )
        )

        # ------------------------------------------------------------------
        # (d) 汇总和返回
        # ------------------------------------------------------------------
        # 计算整个 Skill 的总耗时（毫秒）。
        # (time.monotonic() - t0): 从开始到现在的总秒数
        # * 1000: 转换为毫秒
        total_ms = (time.monotonic() - t0) * 1000

        # 记录完成日志，包含主题、步骤数、总耗时。
        # round(total_ms): 将毫秒数四舍五入为整数，让日志更简洁可读。
        logger.info("deep_research_completed", topic=topic, step_count=len(steps), total_ms=round(total_ms))

        # 返回 SkillResult，包含三个部分：
        #   1. output: 给用户看的研究报告文本（Markdown 格式）
        #   2. steps: 完整的执行步骤记录（3 个 AgentStep）
        #   3. data: 结构化数据，包含主题、知识库来源数、网络来源数
        #      这些数据可供下游组件（如前端 UI）使用，展示来源统计
        return SkillResult(
            output=output,
            steps=steps,
            data={
                "topic": topic,                       # 研究主题
                "doc_sources": len(doc_results.chunks),   # 知识库来源数
                "web_sources": len(web_results.results),  # 网络来源数
            },
        )
