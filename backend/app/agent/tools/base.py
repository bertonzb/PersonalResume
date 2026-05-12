from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class ToolInput(BaseModel):
    """Tool 入参基类。"""
    pass


class ToolOutput(BaseModel):
    """Tool 出参基类。"""
    pass


class BaseTool(ABC):
    """Tool 抽象基类。

    name: Tool 名称，供 Agent 识别
    description: 给 LLM 看的描述，说明何时使用、输入输出格式
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, params: ToolInput) -> ToolOutput:
        raise NotImplementedError
