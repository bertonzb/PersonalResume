from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.llm_provider import LLMProvider
from app.core.logging import logger
from app.rag.retriever import Retriever
from app.schemas.chat import SourceItem


@dataclass
class ChatMessageResult:
    reply: str
    sources: list[SourceItem]
    trace_id: str


class ChatService:
    """对话业务逻辑。"""

    def __init__(self, retriever: Retriever | None = None) -> None:
        self.retriever = retriever or Retriever()
        self._llm: ChatOpenAI | None = None

    @classmethod
    def from_request(cls) -> "ChatService":
        return cls()

    @property
    def llm(self):
        """LLM 实例——通过 LLMProvider 创建，支持 API / vLLM / SGLang 切换。"""
        if self._llm is None:
            self._llm = LLMProvider.create()
        return self._llm

    async def process_message(
        self,
        message: str,
        conversation_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ChatMessageResult:
        """处理一条对话消息，基于 RAG 检索回答。"""
        trace_id = str(uuid.uuid4())
        logger.info(
            "chat_message_received",
            trace_id=trace_id,
            conversation_id=str(conversation_id) if conversation_id else None,
            message_length=len(message),
        )

        # 1. 检索相关文档片段
        search_results = await self.retriever.retrieve(
            query=message,
            top_k=5,
            user_id=user_id,
        )

        sources = [
            SourceItem(
                chunk_id=r.chunk_id,
                content=r.content[:200],
                score=round(r.score, 4),
            )
            for r in search_results
        ]

        # 2. 构建结构化 Prompt（场景识别 + Few-Shot + 幻觉抑制）
        system_prompt = self._build_prompt(message, search_results)

        # 3. 调用 LLM
        try:
            response = await self.llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ]
            )
            reply = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("llm_call_failed", trace_id=trace_id, error=str(e))
            reply = f"抱歉，AI 服务暂时不可用: {str(e)}"

        logger.info(
            "chat_response_generated",
            trace_id=trace_id,
            source_count=len(sources),
            reply_length=len(reply),
        )

        return ChatMessageResult(
            reply=reply,
            sources=sources,
            trace_id=trace_id,
        )

    @staticmethod
    def _build_prompt(message: str, search_results: list) -> str:
        """构建结构化 Prompt——场景识别 + Few-Shot + 幻觉抑制。

        两个场景：
        - 客户问答：用户询问知识、概念、流程等
        - 操作指引：用户询问具体操作步骤、配置方法
        """

        # 幻觉抑制规则（所有场景通用）
        hallucination_rules = (
            "【回答规则——必须严格遵守】\n"
            "1. 只能基于「参考资料」中的内容回答，不得编造任何信息。\n"
            "2. 如果参考资料中没有相关信息，必须明确说：\"当前知识库中没有相关信息，建议上传相关文档。\"\n"
            "3. 不要猜测、不要推断、不要补充参考资料之外的内容。\n"
            "4. 每条回答必须标注引用来源编号，格式为 [来源 N]。\n"
            "5. 如果引用多条来源，需要说明每条来源分别提供了什么信息。"
        )

        # Few-Shot 示例
        few_shot = (
            "【回答示例】\n"
            "示例 1——客户问答：\n"
            "用户问：\"DeepScribe 是什么？\"\n"
            "参考资料：[来源 1] DeepScribe 是一个基于 RAG 技术的个人知识库深度研究助手。\n"
            "正确回答：\"根据知识库资料，DeepScribe 是一个基于 RAG 技术的个人知识库深度研究助手 [来源 1]。\"\n\n"
            "示例 2——操作指引：\n"
            "用户问：\"如何配置 Redis 连接？\"\n"
            "参考资料：[来源 1] 在配置文件中设置 REDIS_URL=redis://localhost:6379/0\n"
            "正确回答：\"配置 Redis 连接的步骤：在配置文件中设置 REDIS_URL=redis://localhost:6379/0 即可 [来源 1]。\"\n\n"
            "示例 3——知识库无相关信息：\n"
            "用户问：\"什么是区块链？\"\n"
            "参考资料：无相关结果\n"
            "正确回答：\"当前知识库中没有关于区块链的相关信息，建议上传相关文档后再提问。\""
        )

        # 场景判断
        operation_keywords = ["怎么", "如何", "步骤", "配置", "设置", "安装", "部署", "启动", "运行", "命令"]
        is_operation = any(kw in message for kw in operation_keywords)

        if search_results:
            context_parts = "\n\n---\n\n".join(
                f"[来源 {i+1}] {r.content}" for i, r in enumerate(search_results)
            )
            scene_instruction = (
                "你正在回答一个\u201c操作指引\u201d类问题。请：\n"
                "1. 列出清晰的步骤\n"
                "2. 如有代码/命令，用代码块展示\n"
                "3. 标注每个步骤的来源编号"
            ) if is_operation else (
                "你正在回答一个\u201c知识问答\u201d类问题。请：\n"
                "1. 先给出简洁的核心答案\n"
                "2. 然后提供详细解释\n"
                "3. 标注每条信息的来源编号"
            )
            prompt = (
                f"{hallucination_rules}\n\n"
                f"{few_shot}\n\n"
                f"【当前场景】{scene_instruction}\n\n"
                f"## 参考资料\n\n{context_parts}"
            )
        else:
            prompt = (
                f"{hallucination_rules}\n\n"
                f"{few_shot}\n\n"
                "【当前场景】知识库中没有与用户问题相关的文档。\n"
                "请直接告知用户，并建议上传相关文档。"
            )

        return prompt
