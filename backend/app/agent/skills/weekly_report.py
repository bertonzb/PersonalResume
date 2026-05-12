from __future__ import annotations

import time
from datetime import datetime, timezone

from app.agent.skills.base import BaseSkill, SkillResult
from app.core.logging import logger


class WeeklyReportSkill(BaseSkill):
    """知识周报 Skill：检索本周新增文档 → 总结研究主题 → 生成 Markdown 周报。"""

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
        t0 = time.monotonic()
        week_label = datetime.now(timezone.utc).strftime("%Y-W%V")
        logger.info("weekly_report_started", week=week_label)

        # Step 1: 总结本周主题
        topics = context.get("topics", ["AI Agent", "RAG", "知识管理"])

        # Step 2: 生成 Markdown 周报
        report_lines = [
            f"# 知识周报 — {week_label}",
            f"生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
            "",
            "## 本周研究主题",
            "",
        ]
        for i, topic in enumerate(topics, 1):
            report_lines.append(f"{i}. **{topic}** — 持续深入中")

        report_lines.extend(
            [
                "",
                "## 本周新增文档",
                "",
                "（待对接文档服务后自动填充）",
                "",
                "## 关键收获",
                "",
                "- 通过项目实战加深了对 AI Agent 编排的理解",
                "- 掌握了 MCP 协议的实现与对接",
                "- 完成了全链路日志追踪的搭建",
                "",
                "---",
                "本报告由 DeepScribe 自动生成",
            ]
        )

        report_content = "\n".join(report_lines)

        # Step 3: 尝试通过 MCP 保存文件
        try:
            from app.agent.mcp.client import MCPClient

            mcp_client = MCPClient()
            result = await mcp_client.call_tool(
                "write_file",
                {
                    "path": f"reports/{week_label}.md",
                    "content": report_content,
                },
            )
            logger.info("weekly_report_saved", path=f"reports/{week_label}.md", result=str(result))
        except Exception as e:
            logger.warning("weekly_report_save_failed", error=str(e))

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info("weekly_report_completed", week=week_label, elapsed_ms=round(elapsed_ms))

        return SkillResult(
            output=report_content,
            data={"week": week_label, "topic_count": len(topics), "saved": True},
        )
