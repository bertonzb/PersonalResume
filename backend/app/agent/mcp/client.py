"""
MCP Client (Model Context Protocol 客户端)
==========================================
本文件实现了 MCP 协议的客户端适配器。

MCP 协议 (Model Context Protocol) 详解：
----------------------------------------
MCP 是由 Anthropic 提出的开放协议，用于标准化 AI Agent 与外部工具/服务之间的通信。
它定义了一套 Client/Server 架构：

  Agent (编排器)
      |
      v
  MCP Client  ───(协议通信)───>  MCP Server  ───>  实际工具/服务
  (本文件)                        (server.py)       (文件系统、数据库等)

核心思想：
- Agent 不需要直接知道每个工具的细节
- 所有工具通过统一的 MCP 协议暴露
- Client 负责发现工具 (list_tools) 和调用工具 (call_tool)

Client/Server 模式在本项目中的应用：
------------------------------------
- MCP Server (server.py)：封装本地文件系统操作（读写文件）
- MCP Client (本文件)：为 Agent 提供统一的工具调用接口
  未来如果要接入更多服务（如数据库、API），只需新增 MCP Server

两个核心方法：
- list_tools() : 向 Server 查询有哪些可用的工具
- call_tool()  : 调用指定的工具并获取结果
"""

from __future__ import annotations

import json
from typing import Any

from app.agent.mcp.server import LocalMCPServer
from app.core.logging import logger


class MCPClient:
    """
    MCP Client 适配器。

    职责：
    - 连接 MCP Server（本地或远程）
    - 为 Agent 提供统一的工具调用接口
    - 管理工具列表缓存（避免重复查询）

    使用示例：
    ---------
        client = MCPClient()
        tools = await client.list_tools()  # 获取可用工具列表
        result = await client.call_tool("read_file", {"path": "notes.txt"})
    """

    def __init__(self, server: LocalMCPServer | None = None) -> None:
        """
        初始化 MCP 客户端。

        参数：
        -----
        server : LocalMCPServer | None
            要连接的 MCP Server 实例。
            如果为 None，则自动创建一个默认的 LocalMCPServer。
            允许传入自定义 Server 是为了方便测试（可以传入 mock server）。
        """
        self.server = server or LocalMCPServer()

        # ---- 工具列表缓存 ----
        # _tools_cache 以 None 开头表示"尚未加载"。
        # 首次调用 list_tools() 时从 Server 获取并缓存结果，
        # 后续调用直接返回缓存，避免重复的网络/IPC 开销。
        # 这是一个典型的内存缓存模式（cache-aside pattern）。
        self._tools_cache: list[dict[str, Any]] | None = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        从 MCP Server 获取可用工具列表。

        这是 MCP 协议的核心操作之一，相当于问 Server："你能做什么？"

        返回格式：
        ---------
        [
            {
                "name": "read_file",
                "description": "读取工作区中的文件内容",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "将内容写入工作区中的文件",
                "inputSchema": { ... }
            }
        ]

        缓存策略：
        ---------
        首次调用时从 Server 获取并缓存，后续直接返回缓存。
        这假设工具列表在运行期间不会变化（对于本地 Server 是合理的）。
        如果需要支持动态工具列表，可以移除缓存逻辑。
        """
        if self._tools_cache is None:
            # 首次调用：从 Server 获取工具列表
            self._tools_cache = await self.server.list_tools()
            logger.info("mcp_tools_listed", count=len(self._tools_cache))
        return self._tools_cache

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        通过 MCP 协议调用指定的工具。

        这是 MCP 协议最核心的方法，相当于对 Server 说："帮我执行这个操作"。

        参数：
        -----
        name : str
            工具名称，如 "read_file"、"write_file"
            必须先通过 list_tools() 获取支持的名称列表
        args : dict
            传给工具的参数，格式由工具的 inputSchema 定义
            例如 write_file 需要 {"path": "xxx", "content": "yyy"}

        返回：
        ------
        dict : 工具执行结果
            - 成功时包含具体的数据内容
            - 失败时可能包含 "error" 字段

        处理细节：
        ---------
        1. 记录调用日志（截取参数前 200 字符，防止日志过大）
        2. 将调用委托给 self.server.call_tool()（即 server.py 中的 LocalMCPServer）
        3. 如果 Server 返回的是 JSON 字符串，先解析为字典再返回
           Server 可能返回 str 或 dict，这里做了兼容处理
        """
        # 记录工具调用日志
        # str(args)[:200] 截断防止参数过长撑爆日志
        logger.info("mcp_tool_called", tool=name, args=str(args)[:200])

        # 委托给 Server 执行实际的工具操作
        result = await self.server.call_tool(name, args)

        # 结果解析：
        # Server 的 call_tool 返回的是 JSON 字符串（如 '{"path": "x", "content": "y"}'）
        # 这里将其解析为 Python 字典，方便上层使用
        # 如果 result 已经是 dict（兼容性处理），则直接使用
        parsed = json.loads(result) if isinstance(result, str) else result
        return parsed
