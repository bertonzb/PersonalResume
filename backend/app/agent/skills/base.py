"""
===============================================================================
文件名称: base.py
所属模块: app.agent.skills (Agent 技能模块)
项目角色: 定义所有 Skill 的抽象基类和执行结果模型。

Skill（技能）与 Tool（工具）的区别 —— 这是理解 Agent 架构的关键：

  Tool（工具）:
    - 最小的执行单元，完成一个原子任务
    - 例如：doc_retrieval（检索文档）、web_search（搜索网络）
    - 一个 Tool 对应一个具体的 API 调用或操作

  Skill（技能）:
    - 多个 Tool 的组合编排，完成一个复杂任务
    - 例如：DeepResearch（深度研究）= 文档检索 + 网络搜索 + 摘要生成
    - 一个 Skill 包含多个步骤（AgentStep），每个步骤调用一个 Tool

类比：
  Tool 像"锤子"、"锯子"（单个工具）
  Skill 像"制作一张桌子"（组合多个工具完成一件完整的事）

关键概念：
  - @dataclass: Python 装饰器，自动生成 __init__、__repr__、__eq__ 等方法。
    用于简化数据类的定义。相比于普通类，不需要手写 __init__ 方法。
  - field(default_factory=list): dataclass 的 field() 函数。
    为可变默认值（list、dict）提供工厂函数。为什么不能直接用 []？
    因为 Python 的默认参数在函数定义时只计算一次，如果直接用 []，
    所有实例会共享同一个 list 对象（这是 Python 的经典陷阱）。
    default_factory=lambda: [] 等价写法。
  - AgentStep: 编排器（Orchestrator）中记录的每一步执行信息。
    包含步骤编号、工具名称、输入、输出、状态、耗时等。
===============================================================================
"""

# ---------------------------------------------------------------------------
# (1) 导入区
# ---------------------------------------------------------------------------

# 延迟类型注解求值
from __future__ import annotations

# ABC: Abstract Base Class，Python 的抽象基类
# abstractmethod: 抽象方法装饰器，子类必须实现
from abc import ABC, abstractmethod

# @dataclass: 装饰器，自动生成 __init__、__repr__ 等方法
# field: dataclass 的字段配置函数，用于设置默认值工厂等
from dataclasses import dataclass, field

# AgentStep: 从编排器模块导入的步骤记录类。
# AgentStep 记录了 Agent 执行过程中每一步的详细信息：
#   - step_number: 步骤编号
#   - tool_name: 使用的工具名称
#   - input: 输入内容
#   - output: 输出内容
#   - status: 执行状态（如 "done"、"failed"）
#   - duration_ms: 执行耗时（毫秒）
from app.agent.orchestrator import AgentStep


# ---------------------------------------------------------------------------
# (2) SkillResult - Skill 执行结果的数据类
# ---------------------------------------------------------------------------

@dataclass
class SkillResult:
    """
    Skill 执行结果。

    当 Agent 执行完一个 Skill 后，会返回 SkillResult 对象，
    其中包含了最终输出文本和完整的执行过程记录。

    @dataclass 装饰器的作用：
      自动生成 __init__()、__repr__()、__eq__() 等方法。
      例如你可以直接写：
        result = SkillResult(output="hello")
        print(result)  # SkillResult(output='hello', steps=[], data={})

    字段说明：
        output (str): Skill 的最终输出文本（给用户看的内容）
        steps (list[AgentStep]): 执行过程中每一步的详细记录，
             用于展示执行过程、调试和性能分析
        data (dict): 额外的结构化数据，供下游组件使用
    """

    # output: 最终输出给用户的文本内容
    output: str

    # steps: 执行步骤列表。
    # field(default_factory=list) 为什么这样写？
    #   因为 list 是可变类型（mutable），如果直接写 steps: list = []，
    #   所有 SkillResult 实例会共享同一个列表对象。
    #   用 default_factory=list 确保每次创建实例时都生成一个新的空列表。
    #   default_factory 接收一个可调用对象，在实例化时会调用它来获取默认值。
    steps: list[AgentStep] = field(default_factory=list)

    # data: 额外的结构化数据字典。
    # 例如 DeepResearchSkill 会在此存放 topic、doc_sources、web_sources 等。
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# (3) BaseSkill - 所有 Skill 的抽象基类
# ---------------------------------------------------------------------------

class BaseSkill(ABC):
    """
    Skill 抽象基类。

    Skill 是多个 Tool 的组合编排。每个具体 Skill 继承此类，
    实现 execute() 方法，在其中按步骤调用多个 Tool 完成复杂任务。

    这个类与 BaseTool 的设计模式相同（Template Method 模式）：
      - 基类定义接口规范（name, description, execute）
      - 子类提供具体实现
      - Agent 编排器通过统一接口调用任意 Skill

    类属性：
        name (str): Skill 名称，供 Agent 识别和调度
        description (str): 给 LLM 看的描述，说明何时触发此 Skill

    抽象方法：
        execute(context) -> SkillResult: 执行 Skill 的主入口
    """

    # name: Skill 的唯一标识名称
    name: str

    # description: 给 LLM 看的 Skill 描述。
    # LLM 阅读此描述来决定是否触发该 Skill。
    # 描述应说明：触发条件、Skill 做了什么、预期结果是什么。
    description: str

    @abstractmethod
    async def execute(self, context: dict) -> SkillResult:
        """
        执行 Skill（异步抽象方法）。

        参数：
            context (dict): 上下文字典，包含了执行 Skill 所需的所有信息。
                           例如 {"topic": "量子计算的未来发展趋势"}
                           context 的内容因 Skill 而异，由调用方（编排器）负责构建。

        返回：
            SkillResult: 包含输出文本、执行步骤和结构化数据的执行结果。

        注意：
            @abstractmethod 要求所有子类必须实现此方法。
            如果子类没有实现，实例化时会抛出 TypeError。
        """
        raise NotImplementedError
