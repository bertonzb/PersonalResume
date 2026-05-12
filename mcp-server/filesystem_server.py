#!/usr/bin/env python3
"""
DeepScribe MCP Server — 本地文件系统操作

实现 MCP 协议基础接口，供 Agent 通过标准化协议调用文件操作。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

WORKSPACE_DIR = Path("./deepscribe_workspace")


def ensure_workspace() -> Path:
    """确保工作区目录存在。"""
    WORKSPACE_DIR.mkdir(exist_ok=True)
    return WORKSPACE_DIR


def list_tools() -> list[dict]:
    """返回可用工具列表（MCP tools/list 协议）。"""
    return [
        {
            "name": "read_file",
            "description": "读取工作区中的文件内容",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于工作区的文件路径",
                    }
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
                    "path": {
                        "type": "string",
                        "description": "相对于工作区的文件路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "list_files",
            "description": "列出工作区中的所有文件",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


def call_tool(name: str, args: dict) -> str:
    """调用指定工具（MCP tools/call 协议）。"""
    ws = ensure_workspace()

    if name == "read_file":
        filepath = ws / args["path"]
        # 安全检查：防止路径穿越
        filepath = ws / os.path.normpath(args["path"]).lstrip("/")
        if not str(filepath.resolve()).startswith(str(ws.resolve())):
            return json.dumps({"error": "路径超出工作区范围"})
        if not filepath.exists():
            return json.dumps({"error": f"文件不存在: {args['path']}"})
        content = filepath.read_text(encoding="utf-8")
        return json.dumps({"path": args["path"], "content": content})

    elif name == "write_file":
        filepath = ws / os.path.normpath(args["path"]).lstrip("/")
        if not str(filepath.resolve()).startswith(str(ws.resolve())):
            return json.dumps({"error": "路径超出工作区范围"})
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(args["content"], encoding="utf-8")
        return json.dumps({"path": args["path"], "written": True})

    elif name == "list_files":
        files = []
        for f in ws.rglob("*"):
            if f.is_file():
                files.append(str(f.relative_to(ws)))
        return json.dumps({"files": sorted(files)})

    else:
        return json.dumps({"error": f"未知工具: {name}"})


def main():
    """MCP Server 主循环：从 stdin 读取 JSON-RPC 请求，处理并返回。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            method = request.get("method", "")
            req_id = request.get("id")

            if method == "tools/list":
                response = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": list_tools()}}
            elif method == "tools/call":
                params = request.get("params", {})
                result = call_tool(params.get("name", ""), params.get("arguments", {}))
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": result}]},
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"未知方法: {method}"},
                }
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if "request" in dir() else None,
                "error": {"code": -32603, "message": str(e)},
            }

        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
