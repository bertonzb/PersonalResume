"""
===============================================================================
文件名称: base.py
所属模块: app.agent.tools (Agent 工具模块)
项目角色: 定义所有 Tool 的抽象基类和输入/输出数据模型。

Tool（工具）是 Agent 的最小执行单元——每个 Tool 负责完成一个具体的原子任务
（例如搜索文档、搜索网络、生成摘要）。所有具体的 Tool 都必须继承 BaseTool
并实现 execute() 方法。

本文件同时定义了 ToolInput 和 ToolOutput 两个 Pydantic 基类，用于规范
每个 Tool 的入参和出参类型，让 LLM（大语言模型）能够理解工具的接口契约。

关键概念：
  - ABC (Abstract Base Class): Python 内置的抽象基类，用于定义接口规范。
    继承 ABC 的类不能直接实例化，子类必须实现所有 @abstractmethod 装饰的方法。
  - @abstractmethod: 装饰器，标记一个方法为抽象方法。子类必须重写该方法，
    否则无法实例化。这是一种"强制接口契约"。
  - Pydantic BaseModel: 一个数据验证库的核心类。继承它后可以自动获得
    类型校验、JSON序列化、Field 描述等功能。
===============================================================================
"""

# ---------------------------------------------------------------------------
# (1) 导入区 - 引入项目所需的依赖
# ---------------------------------------------------------------------------

# from __future__ import annotations: Python 3.7+ 的特性。
# 作用：把所有类型注解中的类型名延迟求值（PEP 563），让代码中的类型引用
# 可以使用"前向引用"（即在类定义完成之前引用该类自身）。
# 例如：在 BaseTool 中可以用 BaseTool 作为参数类型，而不会报 NameError。
from __future__ import annotations

# ABC: Abstract Base Class 的缩写，Python 标准库 abc 模块中提供的抽象基类。
# 继承 ABC 的类成为"抽象类"，不能直接实例化，只能被继承。
# abstractmethod: 装饰器，把方法声明为"抽象方法"。子类必须实现该方法，
# 否则 Python 在尝试实例化子类时会抛出 TypeError。
from abc import ABC, abstractmethod

# BaseModel: Pydantic 库提供的基类。继承它之后，类自动获得：
#   - 类型校验（传入错误类型会报错）
#   - JSON 序列化/反序列化（.model_dump() / .model_validate()）
#   - Field 描述功能（用于给 LLM 说明字段含义）
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# (2) ToolInput - 所有 Tool 入参的基类
# ---------------------------------------------------------------------------

class ToolInput(BaseModel):
    """
    Tool 入参基类。

    所有具体 Tool 的输入参数类都应该继承此类。
    例如 DocRetrievalInput 就继承 ToolInput，并添加一个 query 字段。

    为什么需要这个基类？
      - 统一类型：BaseTool.execute() 的签名中可以用 ToolInput 作为参数类型
      - 可扩展：将来可以在基类中添加公共字段（如 trace_id）
      - 类型安全：类型检查器能识别所有 ToolInput 子类

    继承关系：
      BaseModel (Pydantic)  <--  ToolInput  <--  DocRetrievalInput / WebSearchInput / ...
    """
    pass  # 当前是空基类，仅用于类型标记，不添加额外字段


# ---------------------------------------------------------------------------
# (3) ToolOutput - 所有 Tool 出参的基类
# ---------------------------------------------------------------------------

class ToolOutput(BaseModel):
    """
    Tool 出参基类。

    所有具体 Tool 的输出结果类都应该继承此类。
    例如 DocRetrievalOutput 就继承 ToolOutput，并添加一个 chunks 字段。

    设计与 ToolInput 对称，用于规范返回值格式。
    """
    pass  # 当前是空基类，仅用于类型标记


# ---------------------------------------------------------------------------
# (4) BaseTool - 所有 Tool 的抽象基类（核心！）
# ---------------------------------------------------------------------------

class BaseTool(ABC):
    """
    Tool 抽象基类。

    这是整个 Agent 工具系统的核心抽象。每一个具体的工具（如文档检索、网络搜索、
    摘要生成）都必须继承此类并实现 execute() 方法。

    类属性：
        name (str): Tool 名称 —— 供 Agent 编排器识别和调度。
                    例如 "doc_retrieval"、"web_search"。
        description (str): 给 LLM（大语言模型）看的工具说明 —— 描述何时使用
                           该工具、输入需要什么、输出返回什么。
                           LLM 通过阅读此描述来决定是否调用该工具。

    抽象方法：
        execute(params) -> ToolOutput: 每个子类必须实现的执行入口。
    """

    # name: 工具名称。子类需要覆盖这个类属性。
    # 例如 class DocRetrievalTool(BaseTool): name = "doc_retrieval"
    name: str

    # description: 给 LLM 看的工具描述。LLM 会根据这段描述判断何时使用这个工具。
    # 通常应包含：触发条件、输入格式、输出格式。
    description: str

    @abstractmethod
    async def execute(self, params: ToolInput) -> ToolOutput:
        """
        执行工具的抽象方法（异步）。

        每个子类必须实现这个方法。Agent 编排器会调用此方法来执行具体任务。

        @abstractmethod 装饰器的作用：
          - 标记此方法为抽象方法
          - 子类如果没有实现此方法，则在尝试实例化时会抛出 TypeError
          - 这是一种编译期/运行期的接口契约检查

        参数：
            params (ToolInput): 工具的输入参数，具体类型由子类决定。
                               例如 DocRetrievalTool 接受 DocRetrievalInput。

        返回：
            ToolOutput: 工具的执行结果，具体类型由子类决定。
                       例如 DocRetrievalTool 返回 DocRetrievalOutput。

        异常：
            NotImplementedError: 如果子类没有实现此方法，这里只是占位抛出。
        """
        raise NotImplementedError
