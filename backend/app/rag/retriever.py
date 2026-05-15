# =============================================================================
# 文件：app/rag/retriever.py
# 作用：混合检索器——向量语义检索 + 关键词精确匹配 + Rerank 重排序。
#       三阶段管道：粗排（向量）→ 补充（关键词）→ 精排（Rerank）
# =============================================================================
from __future__ import annotations
import re
from uuid import UUID
from app.core.logging import logger
from app.rag.embedding import EmbeddingService
from app.rag.reranker import BaseReranker, PassThroughReranker
from app.rag.vector_store import ChromaVectorStore, SearchResult, VectorStore


class Retriever:
    """混合检索器——三阶段管道。

    1. 向量语义检索 → 召回语义相关的候选
    2. 关键词精确匹配 → 补充命中关键词的片段
    3. Rerank 重排序 → 精排并截取 Top-K
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        reranker: BaseReranker | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or ChromaVectorStore()
        # Reranker：当前为透传占位，后续换 BGE-Reranker
        self.reranker = reranker or PassThroughReranker()
        # 关键词索引：doc_id → chunks（内存缓存）
        self._keyword_index: dict[str, list[str]] = {}

    async def ingest_document(self, doc_id: UUID, content: str, chunk_size: int = 1000) -> int:
        """摄入文档：分块 → 向量化 → 入库 + 建立关键词索引。"""
        chunks = self._chunk_text(content, chunk_size)
        if not chunks:
            logger.warning("document_empty", doc_id=str(doc_id))
            return 0

        embeddings = await self.embedding_service.embed_texts(chunks)
        await self.vector_store.add_documents(doc_id=doc_id, chunks=chunks, embeddings=embeddings)

        # 建立关键词索引
        self._keyword_index[str(doc_id)] = chunks

        logger.info("document_ingested", doc_id=str(doc_id), chunk_count=len(chunks))
        return len(chunks)

    async def retrieve(
        self, query: str, top_k: int = 5, user_id: UUID | None = None
    ) -> list[SearchResult]:
        """混合检索：向量 + 关键词 → Rerank 精排。"""

        # ===== 阶段 1：向量语义检索（粗排，多召回一些） =====
        query_embedding = await self.embedding_service.embed_query(query)
        vector_results = await self.vector_store.search(
            query_embedding=query_embedding, top_k=max(top_k * 2, 10), user_id=user_id,
        )

        # ===== 阶段 2：关键词精确匹配（补充） =====
        kw_results = self._keyword_search(query)

        # 合并去重
        merged = self._merge_results(vector_results, kw_results)

        # ===== 阶段 3：Rerank 精排 =====
        final = await self.reranker.rerank(query, merged, top_k)

        logger.info(
            "retrieval_completed",
            query=query[:50],
            vector=len(vector_results),
            keyword=len(kw_results),
            final=len(final),
        )
        return final

    # ---- 关键词匹配 ----
    def _keyword_search(self, query: str) -> list[SearchResult]:
        """关键词精确匹配：查询中的词命中文档内容即召回。

        适用：术语查询、编号、具体操作名等精确场景。
        """
        results: list[SearchResult] = []
        keywords = set(re.findall(r'[\u4e00-\u9fff\w]+', query.lower()))
        if not keywords:
            return results

        for doc_id, chunks in self._keyword_index.items():
            for i, chunk in enumerate(chunks):
                if any(kw in chunk.lower() for kw in keywords):
                    results.append(SearchResult(
                        chunk_id=f"{doc_id}:{i}", content=chunk, score=0.9))
        return results

    # ---- 合并去重 ----
    @staticmethod
    def _merge_results(
        vector: list[SearchResult], keyword: list[SearchResult]
    ) -> list[SearchResult]:
        """合并去重：同 chunk_id 保留得分更高的。"""
        seen: dict[str, SearchResult] = {}
        for r in vector:
            seen[r.chunk_id] = r
        for r in keyword:
            if r.chunk_id not in seen or r.score > seen[r.chunk_id].score:
                seen[r.chunk_id] = r
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)

    # ---- 文本分块 ----
    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
        """文本分块：优先在句号/换行处断开，保持语义完整。"""
        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break

            chunk = text[start:end]
            for sep in ["\n\n", "\n", "。", ".", "！", "？"]:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size // 2:
                    end = start + last_sep + len(sep)
                    break

            chunks.append(text[start:end].strip())
            start = end

        return [c for c in chunks if c]
