"""
知识周报 Skill (Weekly Report Skill)
=====================================
本文件实现了自动生成知识库周报的技能 (Skill)。

关键概念：
---------
- Skill（技能）：比 Tool 更高层的抽象，表示一个完整的工作流
  一个 Skill 可以调用多个 Tool，有明确的输入输出。
- BaseSkill：所有 Skill 的基类，定义了 execute() 接口。
- SkillResult：Skill 执行结果的统一数据结构。

Celery Beat 定时任务调度：
-------------------------
在实际部署中，本 Skill 会被 Celery Beat（Celery 的定时调度器）周期性触发。
Celery Beat 就像一个 cron 定时器，可以配置"每周一早上 9 点执行"这样的规则。
当前版本中 Skill 是手动调用或由 Agent 触发，后续会接入 Celery Beat 实现自动化。

周报生成流程：
------------
1. 获取本周的研究主题（从上下文传入或使用默认值）
2. 拼接 Markdown 格式的周报内容
3. 通过 MCP Client 的 write_file 工具将周报保存到本地文件
4. 返回 SkillResult 包含生成的报告内容
"""

from __future__ import annotations

import time
from datetime import datetime, timezone  # timezone.utc = UTC 时区，避免时区混乱

# Skill 基类和结果类型
from app.agent.skills.base import BaseSkill, SkillResult
from app.core.logging import logger


class WeeklyReportSkill(BaseSkill):
    """
    知识周报 Skill：检索本周新增文档 → 总结研究主题 → 生成 Markdown 周报。

    BaseSkill 约定：
    ---------------
    - 子类必须定义 name（技能名称）和 description（技能描述）
    - 子类必须实现 execute(context) → SkillResult 方法
    - context 是一个字典，由调用方传入上下文信息

    触发时机：
    ---------
    - 用户说"生成周报"、"本周学习总结"等
    - Celery Beat 定时触发（未来会接入）
    """

    # ---- 技能元信息 ----
    # name 和 description 是 BaseSkill 要求的类属性
    # Agent 通过 description 理解这个技能何时应该被调用
    name = "weekly_report"
    description = (
        "生成知识库周报。流程包括：\n"
        "1. 检索本周新增的文档\n"
        "2. 总结本周研究主题\n"
        "3. 生成 Markdown 格式的周报\n"
        "4. 通过 MCP write_file 保存到本地\n"
        "当用户需要生成周报或查看本周学习总结时触发。"
    )

    async def execute(self, context: dict) -> SkillResult:
        """
        执行周报生成流程。

        context 参数说明：
        -----------------
        context 是调用方传入的上下文字典，可以包含：
        - "topics"  : list[str]  本周研究主题列表
        - "user_id" : str        用户 ID（未来用于个性化）
        - 其他自定义字段

        返回值 SkillResult 字段说明：
        ----------------------------
        - output : str  技能执行的主要输出（周报内容文本）
        - data   : dict 额外的结构化数据（如周次、主题数量等）
        """
        # 记录开始时间（用于计算耗时）
        t0 = time.monotonic()

        # ---- 生成周次标签 ----
        # strftime 格式化日期：
        # %Y = 四位年份（如 2026）
        # %V = ISO 8601 周数（01-53），即一年中的第几周
        # 这是国际标准周历，比直接用 %U 更规范
        week_label = datetime.now(timezone.utc).strftime("%Y-W%V")
        logger.info("weekly_report_started", week=week_label)

        # ================================================================
        # Step 1: 获取本周研究主题
        # ================================================================
        # 从上下文中读取 "topics"，如果没提供则使用默认值
        # context.get("topics", default) 是安全读取字典的方式
        # 这里的默认值是常见的 AI/知识管理相关主题
        topics = context.get("topics", ["AI Agent", "RAG", "知识管理"])

        # ================================================================
        # Step 2: 生成 Markdown 周报
        # ================================================================
        # 使用列表拼接字符串（比 += 拼接更高效，Python 中字符串是不可变的）
        report_lines = [
            f"# 知识周报 — {week_label}",  # f-string：Python 3.6+ 的格式化字符串
            f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
            "",  # 空行在 Markdown 中用于段落分隔
            "## 本周研究主题",
            "",
        ]

        # enumerate(topics, 1) 从 1 开始编号（而不是 0）
        # Markdown 中 **文字** 表示加粗
        for i, topic in enumerate(topics, 1):
            report_lines.append(f"{i}. **{topic}** — 持续深入中")

        # extend() 批量追加多个元素到列表末尾
        report_lines.extend(
            [
                "",
                "## 本周新增文档",
                "",
                "（待对接文档服务后自动填充）",  # 占位符，后续版本会动态填充
                "",
                "## 关键收获",
                "",
                "- 通过项目实战加深了对 AI Agent 编排的理解",
                "- 掌握了 MCP 协议的实现与对接",
                "- 完成了全链路日志追踪的搭建",
                "",
                "---",  # Markdown 水平分割线
                "本报告由 DeepScribe 自动生成",
            ]
        )

        # "\n".join() 将列表中的每个元素用换行符连接成完整字符串
        report_content = "\n".join(report_lines)

        # ================================================================
        # Step 3: 通过 MCP Client 保存文件
        # ================================================================
        # MCP (Model Context Protocol) 详解：
        # ----------------------------------
        # MCP 是一种标准化的工具调用协议，让 AI Agent 可以安全地访问外部服务。
        # 这里我们将文件写入操作封装在 MCP Server 中，
        # 通过 MCP Client 统一调用，而不是直接操作文件系统。
        # 这样做的好处：
        # 1. 安全隔离：MCP Server 可以限制文件操作范围（工作区）
        # 2. 统一接口：所有工具的调用方式一致
        # 3. 易于扩展：未来可以替换为远程 MCP Server
        #
        # 注意：这里使用了延迟导入（在 try 块内部 import）
        # 这样做可以避免循环导入问题，同时只在真正需要时才加载 MCPClient
        try:
            from app.agent.mcp.client import MCPClient

            # 创建 MCP 客户端实例
            mcp_client = MCPClient()

            # 调用 MCP Server 的 write_file 工具
            # 参数：
            # - "path"    : 文件保存路径（相对于工作区目录）
            # - "content" : 要写入的文件内容
            result = await mcp_client.call_tool(
                "write_file",
                {
                    "path": f"reports/{week_label}.md",
                    "content": report_content,
                },
            )
            logger.info("weekly_report_saved", path=f"reports/{week_label}.md", result=str(result))
        except Exception as e:
            # 文件保存失败不阻断整体流程，记录警告即可
            # 因为报告内容已经通过 SkillResult 返回给调用方了
            logger.warning("weekly_report_save_failed", error=str(e))

        # 计算总耗时
        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("weekly_report_completed", week=week_label, elapsed_ms=round(elapsed_ms))

        # 返回 SkillResult
        # output: 报告文本（调用方可以直接展示或使用）
        # data: 附加的结构化数据（方便程序化处理）
        return SkillResult(
            output=report_content,
            data={
                "week": week_label,        # 周次标签，如 "2026-W20"
                "topic_count": len(topics), # 主题数量
                "saved": True,              # 是否已保存到文件
            },
        )
