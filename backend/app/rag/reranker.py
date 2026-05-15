# =============================================================================
# 文件：app/rag/reranker.py
# 作用：Rerank 重排序模块——对粗排结果进行精细重排，提升检索精准度。
#       当前为接口预留层，后续可接入 BGE-Reranker 等模型。
# =============================================================================
from __future__ import annotations
from abc import ABC, abstractmethod
from app.rag.vector_store import SearchResult


class BaseReranker(ABC):
    """重排序器抽象接口。

    检索管道：向量/关键词粗排 → Reranker 精排 → 返回 Top-K
    当前为占位实现（直接透传），后续可替换为 BGE-Reranker 等模型。
    """

    @abstractmethod
    async def rerank(self, query: str, candidates: list[SearchResult], top_k: int = 5) -> list[SearchResult]:
        """对候选结果重排序。

        参数：
            query：原始查询文本
            candidates：粗排阶段返回的候选结果列表
            top_k：最终保留的前 K 个结果

        返回：重排序后的结果列表（按相关性降序）
        """
        raise NotImplementedError


class PassThroughReranker(BaseReranker):
    """占位重排序器：直接透传，不做重排。

    后续可替换为：
    - BGEReranker：基于 BGE-Reranker-v2-m3 等模型
    - CrossEncoderReranker：基于 sentence-transformers CrossEncoder
    """

    async def rerank(self, query: str, candidates: list[SearchResult], top_k: int = 5) -> list[SearchResult]:
        """透传：保持原顺序，仅截取 top_k。"""
        return candidates[:top_k]