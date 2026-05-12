from __future__ import annotations

from uuid import UUID

from app.core.logging import logger
from app.rag.embedding import EmbeddingService
from app.rag.vector_store import ChromaVectorStore, SearchResult, VectorStore


class Retriever:
    """RAG 检索器，组合 Embedding + VectorStore 实现文档索引和检索。"""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or ChromaVectorStore()

    async def ingest_document(self, doc_id: UUID, content: str, chunk_size: int = 1000) -> int:
        """将文档内容分块并向量化后存入向量库。"""
        chunks = self._chunk_text(content, chunk_size)
        if not chunks:
            logger.warning("document_empty", doc_id=str(doc_id))
            return 0

        embeddings = await self.embedding_service.embed_texts(chunks)
        await self.vector_store.add_documents(doc_id=doc_id, chunks=chunks, embeddings=embeddings)

        logger.info(
            "document_ingested",
            doc_id=str(doc_id),
            chunk_count=len(chunks),
        )
        return len(chunks)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        user_id: UUID | None = None,
    ) -> list[SearchResult]:
        """检索与查询最相关的文档片段。"""
        query_embedding = await self.embedding_service.embed_query(query)
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            user_id=user_id,
        )
        logger.info("retrieval_completed", query=query[:50], result_count=len(results))
        return results

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
        """简单分块：按固定长度切分，尝试在句号处断开。"""
        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break

            # 尝试在句号或换行处断开
            chunk = text[start:end]
            for sep in ["\n\n", "\n", "。", ".", "！", "？"]:
                last_sep = chunk.rfind(sep)
                if last_sep > chunk_size // 2:
                    end = start + last_sep + len(sep)
                    break

            chunks.append(text[start:end].strip())
            start = end

        return [c for c in chunks if c]
