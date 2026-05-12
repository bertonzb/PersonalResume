from __future__ import annotations

import json
from typing import Any

from app.agent.mcp.server import LocalMCPServer
from app.core.logging import logger


class MCPClient:
    """MCP Client 适配器，连接 MCP Server 并为 Agent 提供统一的工具调用接口。"""

    def __init__(self, server: LocalMCPServer | None = None) -> None:
        self.server = server or LocalMCPServer()
        self._tools_cache: list[dict[str, Any]] | None = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """从 MCP Server 获取可用工具列表。"""
        if self._tools_cache is None:
            self._tools_cache = await self.server.list_tools()
            logger.info("mcp_tools_listed", count=len(self._tools_cache))
        return self._tools_cache

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """通过 MCP 协议调用工具。"""
        logger.info("mcp_tool_called", tool=name, args=str(args)[:200])
        result = await self.server.call_tool(name, args)
        parsed = json.loads(result) if isinstance(result, str) else result
        return parsed
