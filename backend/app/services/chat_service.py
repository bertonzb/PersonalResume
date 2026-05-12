from __future__ import annotations

import uuid
from dataclasses import dataclass

from langchain_openai import ChatOpenAI

from app.config import get_settings
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
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            settings = get_settings()
            self._llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key or "sk-placeholder",
                temperature=0.3,
            )
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

        # 2. 构建 Prompt
        if search_results:
            context_parts = "\n\n---\n\n".join(
                f"[来源 {i+1}] {r.content}" for i, r in enumerate(search_results)
            )
            system_prompt = (
                "你是一个个人知识库助手。请严格基于以下提供的资料回答问题。"
                "如果资料中没有相关信息，请诚实地说'当前知识库中没有相关信息'。"
                "回答时请引用来源编号。\n\n"
                f"## 参考资料\n\n{context_parts}"
            )
        else:
            system_prompt = (
                "你是一个个人知识库助手。用户的知识库中暂时没有相关文档。"
                "请建议用户上传相关文档后再提问。"
            )

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
