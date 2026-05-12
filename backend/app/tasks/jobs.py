from __future__ import annotations

import uuid

from app.core.logging import logger
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name="ingest_document")
def ingest_document_task(self, doc_id: str, content: str) -> dict:
    """异步处理文档分块+向量化。"""
    logger.info("task_ingest_started", task_id=self.request.id, doc_id=doc_id)
    self.update_state(state="PROGRESS", meta={"progress": 0})

    # 分块
    chunks = _chunk_text(content)
    total = len(chunks)
    self.update_state(state="PROGRESS", meta={"progress": 30, "chunks": total})

    logger.info("task_ingest_completed", task_id=self.request.id, doc_id=doc_id, chunk_count=total)
    return {"doc_id": doc_id, "chunk_count": total, "status": "ready"}


@celery_app.task(bind=True, name="deep_research")
def deep_research_task(self, user_id: str, topic: str) -> dict:
    """异步执行深度研究。"""
    logger.info("task_deep_research_started", task_id=self.request.id, topic=topic)
    self.update_state(state="PROGRESS", meta={"progress": 10})

    # 模拟多步研究过程
    self.update_state(state="PROGRESS", meta={"progress": 50, "phase": "检索知识库"})
    self.update_state(state="PROGRESS", meta={"progress": 80, "phase": "联网搜索"})

    result = {
        "topic": topic,
        "output": f"研究报告: {topic}（异步生成）",
        "status": "done",
    }

    logger.info("task_deep_research_completed", task_id=self.request.id, topic=topic)
    return result


def _chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks
