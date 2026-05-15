# =============================================================================
# 文件：app/tasks/jobs.py
# 作用：定义 Celery 异步任务。前端发起请求后立刻得到响应，
#       耗时操作（文档处理、深度研究）在后台异步执行。
# =============================================================================
from __future__ import annotations
import uuid
from app.core.logging import logger
# celery_app：上面创建的 Celery 实例，用它来注册任务
from app.tasks.celery_app import celery_app


# ---- 异步任务 1：文档摄入 ----
# @celery_app.task(bind=True)：注册为 Celery 任务
# bind=True：把当前任务对象绑定到 self，可以访问 self.request.id（任务ID）和 update_state（报告进度）
# name="ingest_document"：任务的全局唯一名称
@celery_app.task(bind=True, name="ingest_document")
def ingest_document_task(self, doc_id: str, content: str) -> dict:
    """异步处理文档分块+向量化。

    为什么异步？文档可能很长，调用外部 API 耗时长。
    API 立刻返回"任务已接收"，后台慢慢处理。
    """
    # 记录任务开始
    logger.info("task_ingest_started", task_id=self.request.id, doc_id=doc_id)
    # update_state：更新任务状态，前端可轮询查询进度
    self.update_state(state="PROGRESS", meta={"progress": 0})

    # 文本切分成小块
    chunks = _chunk_text(content)
    total = len(chunks)
    # 告诉前端进度到了 30%，并附上切了多少块
    self.update_state(state="PROGRESS", meta={"progress": 30, "chunks": total})

    logger.info("task_ingest_completed", task_id=self.request.id, doc_id=doc_id, chunk_count=total)
    return {"doc_id": doc_id, "chunk_count": total, "status": "ready"}


# ---- 异步任务 2：深度研究 ----
@celery_app.task(bind=True, name="deep_research")
def deep_research_task(self, user_id: str, topic: str) -> dict:
    """异步执行深度研究（由 Celery Beat 定时调度或手动触发）。

    前端调用时可以立刻返回"任务已提交"，然后轮询状态获取进度。
    """
    logger.info("task_deep_research_started", task_id=self.request.id, topic=topic)
    self.update_state(state="PROGRESS", meta={"progress": 10})

    # 模拟多步研究：每一步更新进度和当前阶段描述
    self.update_state(state="PROGRESS", meta={"progress": 50, "phase": "检索知识库"})
    self.update_state(state="PROGRESS", meta={"progress": 80, "phase": "联网搜索"})

    result = {
        "topic": topic,
        "output": f"研究报告: {topic}（异步生成）",
        "status": "done",
    }

    logger.info("task_deep_research_completed", task_id=self.request.id, topic=topic)
    return result


# ---- 工具函数：文本分块 ----
def _chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    """按固定长度切分文本（简化版，Retriever 里有增强版）。"""
    # 文本很短，不需要切分
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    # 循环切：每次取 chunk_size 长度
    while start < len(text):
        # min 防止越界（最后一块可能不够 chunk_size）
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end  # 移动起点
    return chunks
