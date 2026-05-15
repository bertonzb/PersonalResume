"""
自建 MCP Server 封装
====================
本文件实现了本地 MCP (Model Context Protocol) Server。

什么是 MCP Server？
------------------
MCP Server 是 MCP 协议中的服务端，负责：
1. 暴露可用的工具列表（list_tools）
2. 接收工具调用请求并执行（call_tool）
3. 返回执行结果

在本项目中，MCP Server 封装了本地文件系统的读写操作，
供 Agent 通过 MCP 协议安全地操作文件，而非直接调用文件 API。

为什么需要 MCP Server？
----------------------
- 安全隔离：限制文件操作范围在工作区目录内
- 统一接口：所有工具遵循相同的调用规范
- 易于扩展：未来可以添加数据库操作、API 调用等工具
- 标准化：MCP 是开源协议，可以对接任何支持 MCP 的工具

Windows 路径安全（重要！）：
--------------------------
Windows 使用反斜杠 (backslash) 作为路径分隔符，但 Python 可以在 Windows 上使用正斜杠 /。
本文件中的路径处理同时兼容 Windows 和 Linux：
- os.path.join()   : 使用系统正确的分隔符拼接路径
- os.path.normpath(): 规范化路径（将正斜杠和反斜杠统一，消除 .. 和 .）
- os.path.abspath() : 转为绝对路径（用于安全检查）
- full_path.startswith(...) : 防止路径遍历攻击
"""

from __future__ import annotations

"""
将本地文件系统操作暴露为 MCP 协议标准接口。
供 Agent 通过 MCP 协议调用文件操作，而非直接调用 Tools。
"""

import asyncio  # Python 标准异步 I/O 库
import json
import os
from typing import Any


class LocalMCPServer:
    """
    本地 MCP Server，封装文件操作。

    支持的 MCP 工具：
    ----------------
    - read_file  : 读取工作区中的文件内容
    - write_file : 将内容写入工作区中的文件

    工作区 (Workspace) 概念：
    ------------------------
    所有文件操作都被限制在 workspace_dir 目录内。
    这是安全隔离的关键——Agent 不能随意读写系统任意位置的文件。
    默认工作区为 "./deepscribe_workspace"（项目相对路径）。
    """

    def __init__(self, workspace_dir: str = "./deepscribe_workspace") -> None:
        """
        初始化本地 MCP Server。

        参数：
        -----
        workspace_dir : str
            工作区根目录路径。所有文件操作都限制在此目录内。
            目录会在初始化时自动创建（如果不存在）。
        """
        self.workspace_dir = workspace_dir
        # os.makedirs 递归创建目录
        # exist_ok=True 表示如果目录已存在也不报错
        os.makedirs(workspace_dir, exist_ok=True)

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        返回 MCP 工具列表 (MCP tools/list 协议)。

        每个工具的定义包含：
        - name        : 工具名称（唯一标识）
        - description : 工具的功能描述
        - inputSchema : 输入参数的 JSON Schema 定义
          - type       : "object" 表示参数是一个对象
          - properties : 每个参数的类型和描述
          - required   : 必填参数列表

        这是 MCP 协议的标准化格式，任何 MCP Client 都能解析。
        """
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
            {
                "name": "query_weather",
                "description": "查询指定城市的实时天气信息。返回温度、天气状况、湿度、风速等。支持中文城市名（如'北京'、'上海'）。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称，如'北京'、'上海'、'Tokyo'、'London'"}
                    },
                    "required": ["city"],
                },
            },
        ]

    async def call_tool(self, name: str, args: dict[str, Any]) -> str:
        """
        调用指定的 MCP 工具 (MCP tools/call 协议)。

        参数：
        -----
        name : str
            工具名称，必须是 list_tools() 中定义的名称之一
        args : dict
            工具参数，格式必须匹配 inputSchema 定义

        返回：
        ------
        str : JSON 格式的执行结果字符串
            - 成功：包含操作结果数据
            - 失败：包含 "error" 字段说明原因
        """
        if name == "read_file":
            return await self._read_file(args.get("path", ""))
        elif name == "write_file":
            return await self._write_file(args.get("path", ""), args.get("content", ""))
        elif name == "query_weather":
            return await self._query_weather(args.get("city", ""))
        else:
            return json.dumps({"error": f"未知工具: {name}"})

    async def _read_file(self, path: str) -> str:
        """
        读取工作区文件。

        Windows 路径安全详解（同样适用于 Linux）：
        -----------------------------------------
        下面三步是防止"路径遍历攻击"的关键安全措施：

        Step 1 - os.path.join(workspace_dir, path)：
            将工作区目录和用户提供的路径拼接起来。
            例如：workspace_dir="./workspace", path="notes.txt"
            结果："./workspace/notes.txt"

        Step 2 - os.path.normpath(full_path)：
            规范化路径，消除路径中的 ".." 和 "."。
            例如："./workspace/../etc/passwd" → "./etc/passwd"
            这是防止攻击者用 .. 跳出工作区的第一道防线。

        Step 3 - full_path.startswith(os.path.abspath(workspace_dir))：
            检查规范化后的路径是否仍然在工作区目录下。
            如果攻击者试图访问工作区外的文件（如 ../../etc/passwd），
            这一步会检测到并拒绝操作。

        Windows 特别注意事项：
        --------------------
        - Windows 中盘符如 C 盘也会被正确比较
        - os.path.abspath 确保两边都是绝对路径的比较
        - 大小写不敏感：Windows 默认不区分大小写，startswith 可能不完美
          （如需加强，可使用 os.path.normcase() 统一大小写）
        """
        # 拼接完整路径
        full_path = os.path.join(self.workspace_dir, os.path.normpath(path))

        # 安全检查：确保最终路径在工作区目录内
        # os.path.abspath 将相对路径转换为绝对路径
        if not full_path.startswith(os.path.abspath(self.workspace_dir)):
            return json.dumps({"error": "路径超出工作区范围"})

        # 检查文件是否存在
        if not os.path.exists(full_path):
            return json.dumps({"error": f"文件不存在: {path}"})

        # ---- 异步文件读取 ----
        # asyncio.get_running_loop() 获取当前正在运行的事件循环
        # loop.run_in_executor(None, func) 在线程池中执行同步函数
        #
        # 为什么需要这样做？
        # - Python 的文件 I/O 是同步阻塞的（open/read/write 会阻塞线程）
        # - 在 async 函数中直接调用阻塞操作会冻结整个事件循环
        # - run_in_executor 将阻塞操作放到单独的线程中执行，不阻塞主循环
        # - 第一个参数 None 表示使用默认的线程池执行器
        loop = asyncio.get_running_loop()
        content = await loop.run_in_executor(
            None,
            # lambda 匿名函数：读取文件全部内容
            # encoding="utf-8" 指定文件编码，处理中文内容
            lambda: open(full_path, "r", encoding="utf-8").read()
        )
        # ensure_ascii=False 确保 JSON 中的中文不会被转义成 \uXXXX
        return json.dumps({"path": path, "content": content}, ensure_ascii=False)

    async def _write_file(self, path: str, content: str) -> str:
        """
        将内容写入工作区文件。

        安全机制与 _read_file 相同，额外增加了：
        - 自动创建目标文件所在的目录（如果不存在）
        - 文件以覆盖模式写入（"w" 模式）

        参数：
        -----
        path : str
            文件路径（相对于工作区）
        content : str
            要写入的文件内容

        返回：
        ------
        str : JSON 格式结果，成功时包含 {"path": "...", "written": true}
        """
        # 拼接完整路径（同 _read_file 的安全处理）
        full_path = os.path.join(self.workspace_dir, os.path.normpath(path))

        # 安全检查：防止路径遍历攻击
        if not full_path.startswith(os.path.abspath(self.workspace_dir)):
            return json.dumps({"error": "路径超出工作区范围"})

        # 自动创建目标文件所在的目录
        # os.path.dirname 获取文件路径中的目录部分
        # 例如：full_path="./workspace/reports/weekly.md"
        #       dirname = "./workspace/reports"
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # 异步写入文件
        # 原理同 _read_file 中的说明
        # "w" 模式 = 覆盖写入（文件存在则清空，不存在则创建）
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: open(full_path, "w", encoding="utf-8").write(content)
        )

        return json.dumps({"path": path, "written": True})

    async def _query_weather(self, city: str) -> str:
        """
        查询城市天气（使用免费的 wttr.in API，无需 API Key）。

        参数：
        -----
        city : str  城市名称（中文或英文均可）

        返回：
        ------
        str : JSON 格式的天气信息
        """
        if not city:
            return json.dumps({"error": "城市名不能为空"})

        try:
            # wttr.in 是一个免费的天气 API，返回 JSON 格式数据
            import urllib.request
            import urllib.parse

            loop = asyncio.get_running_loop()

            def _fetch():
                # URL 编码城市名（中文等特殊字符必须编码）
                encoded_city = urllib.parse.quote(city)
                url = f"https://wttr.in/{encoded_city}?format=j1&lang=zh"
                req = urllib.request.Request(url, headers={"User-Agent": "DeepScribe/0.1"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.read().decode("utf-8")

            raw = await loop.run_in_executor(None, _fetch)
            data = json.loads(raw)

            # 提取当前天气
            current = data.get("current_condition", [{}])[0]
            result = {
                "city": city,
                "temperature": f"{current.get('temp_C', 'N/A')}°C",
                "feels_like": f"{current.get('FeelsLikeC', 'N/A')}°C",
                "weather": current.get("weatherDesc", [{}])[0].get("value", "未知"),
                "humidity": f"{current.get('humidity', 'N/A')}%",
                "wind_speed": f"{current.get('windspeedKmph', 'N/A')} km/h",
                "visibility": f"{current.get('visibility', 'N/A')} km",
            }
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"error": f"天气查询失败: {str(e)}"})
