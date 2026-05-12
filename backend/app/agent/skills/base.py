from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.agent.orchestrator import AgentStep


@dataclass
class SkillResult:
    """Skill 执行结果。"""

    output: str
    steps: list[AgentStep] = field(default_factory=list)
    data: dict = field(default_factory=dict)


class BaseSkill(ABC):
    """Skill 抽象基类。Skill 是多个 Tool 的组合编排。

    name: Skill 名称
    description: 给 LLM 看的描述，说明何时触发此 Skill
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, context: dict) -> SkillResult:
        """执行 Skill。"""
        raise NotImplementedError
