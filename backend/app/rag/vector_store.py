from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.config import get_settings
from app.core.logging import logger


class SearchResult:
    """向量搜索结果。"""

    def __init__(self, chunk_id: str, content: str, score: float) -> None:
        self.chunk_id = chunk_id
        self.content = content
        self.score = score


class VectorStore(ABC):
    """向量库抽象接口。"""

    @abstractmethod
    async def add_documents(
        self,
        doc_id: UUID,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        user_id: UUID | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    async def delete_document(self, doc_id: UUID) -> None:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    """ChromaDB 实现。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = None
        self._collection = None
        self.host = settings.chroma_host
        self.port = settings.chroma_port

    def _ensure_client(self) -> None:
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name="deepscribe_documents"
            )
            logger.info("chromadb_connected", host=self.host, port=self.port)
        except Exception:
            # 开发阶段使用内存模式
            import chromadb

            logger.warning("chromadb_fallback_to_memory")
            self._client = chromadb.Client()
            self._collection = self._client.get_or_create_collection(
                name="deepscribe_documents"
            )

    async def add_documents(
        self,
        doc_id: UUID,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        self._ensure_client()
        ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"doc_id": str(doc_id)} for _ in chunks],
        )
        logger.info("chromadb_documents_added", doc_id=str(doc_id), chunk_count=len(chunks))

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        user_id: UUID | None = None,
    ) -> list[SearchResult]:
        self._ensure_client()
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        search_results: list[SearchResult] = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                content = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = 1.0 - min(distance, 1.0) if distance else 0.0
                search_results.append(SearchResult(chunk_id=chunk_id, content=content, score=score))

        return search_results

    async def delete_document(self, doc_id: UUID) -> None:
        self._ensure_client()
        self._collection.delete(where={"doc_id": str(doc_id)})
        logger.info("chromadb_document_deleted", doc_id=str(doc_id))
