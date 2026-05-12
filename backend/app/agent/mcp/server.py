from __future__ import annotations

"""
自建 MCP Server 封装。

将本地文件系统操作暴露为 MCP 协议标准接口。
供 Agent 通过 MCP 协议调用文件操作，而非直接调用 Tools。
"""

import asyncio
import json
import os
from typing import Any


class LocalMCPServer:
    """本地 MCP Server，封装文件操作。"""

    def __init__(self, workspace_dir: str = "./deepscribe_workspace") -> None:
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)

    async def list_tools(self) -> list[dict[str, Any]]:
        """返回 MCP tools/list。"""
        return [
            {
                "name": "read_file",
                "description": "读取工作区中的文件内容",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"}
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "将内容写入工作区中的文件",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "content": {"type": "string", "description": "写入内容"},
                    },
                    "required": ["path", "content"],
                },
            },
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        """调用指定 MCP Tool。"""
        if name == "read_file":
            return await self._read_file(args.get("path", ""))
        elif name == "write_file":
            return await self._write_file(args.get("path", ""), args.get("content", ""))
        else:
            return json.dumps({"error": f"未知工具: {name}"})

    async def _read_file(self, path: str) -> str:
        """读取工作区文件。"""
        full_path = os.path.join(self.workspace_dir, os.path.normpath(path))
        if not full_path.startswith(os.path.abspath(self.workspace_dir)):
            return json.dumps({"error": "路径超出工作区范围"})

        if not os.path.exists(full_path):
            return json.dumps({"error": f"文件不存在: {path}"})

        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(
            None, lambda: open(full_path, "r", encoding="utf-8").read()
        )
        return json.dumps({"path": path, "content": content}, ensure_ascii=False)

    async def _write_file(self, path: str, content: str) -> str:
        """将内容写入工作区文件。"""
        full_path = os.path.join(self.workspace_dir, os.path.normpath(path))
        if not full_path.startswith(os.path.abspath(self.workspace_dir)):
            return json.dumps({"error": "路径超出工作区范围"})

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: open(full_path, "w", encoding="utf-8").write(content)
        )
        return json.dumps({"path": path, "written": True})
