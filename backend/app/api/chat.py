from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.agent.orchestrator import AgentOrchestrator
from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """向 RAG 助手发送一条对话消息。"""
    result = await chat_service.process_message(
        message=body.message,
        conversation_id=body.conversation_id,
    )
    return ChatResponse(
        id=uuid.uuid4(),
        reply=result.reply,
        sources=result.sources,
        trace_id=result.trace_id,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/agent", response_model=ChatResponse)
async def send_message_agent(
    body: ChatRequest,
) -> ChatResponse:
    """使用 Agent 编排器处理消息——自动选择和调用工具。"""
    orchestrator = AgentOrchestrator()
    result = await orchestrator.run(message=body.message, conversation_id=body.conversation_id)

    steps_json = [
        {
            "step_number": s.step_number,
            "tool_name": s.tool_name,
            "input": s.input,
            "output": s.output,
            "status": s.status,
            "duration_ms": s.duration_ms,
        }
        for s in result.steps
    ]

    return ChatResponse(
        id=uuid.uuid4(),
        reply=result.reply,
        steps=steps_json,
        trace_id=result.trace_id,
        created_at=datetime.now(timezone.utc),
    )
