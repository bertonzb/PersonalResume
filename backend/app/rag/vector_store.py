# =============================================================================
# 文件：app/rag/vector_store.py
# 作用：向量数据库的抽象接口和 ChromaDB 具体实现。
#       向量库 = 存向量（数字数组）+ 找最相似的向量。
#       类比传统数据库存"行"，向量库存"向量"。
# =============================================================================
from __future__ import annotations
# ABC + abstractmethod：抽象基类，强制子类实现某些方法
from abc import ABC, abstractmethod
from uuid import UUID
from app.config import get_settings
from app.core.logging import logger


# ---- 搜索结果数据类 ----
class SearchResult:
    """一条向量搜索结果——包含文档片段ID、内容、相似度分数。"""

    def __init__(self, chunk_id: str, content: str, score: float) -> None:
        self.chunk_id = chunk_id    # 片段唯一 ID（如 "doc-123:0"）
        self.content = content      # 片段文本内容
        self.score = score          # 相似度（0~1，越大越相似）


# ---- 向量库抽象接口 ----
# ABC（Abstract Base Class）：不能直接实例化，只能被继承
# 好处：定义统一接口，以后换 FAISS/Milvus 只需新写一个实现类
class VectorStore(ABC):
    """向量库抽象接口。所有向量库实现都必须提供这三个方法。"""

    @abstractmethod                      # 声明这是一个抽象方法，子类必须覆写
    async def add_documents(             # 添加文档向量到库
        self, doc_id: UUID,              # 文档 ID
        chunks: list[str],               # 文本块列表
        embeddings: list[list[float]],   # 每个文本块的向量
    ) -> None:
        raise NotImplementedError        # 子类不覆写就报这个错

    @abstractmethod
    async def search(                    # 搜索最相似的向量
        self,
        query_embedding: list[float],    # 查询向量
        top_k: int = 5,                  # 返回前 K 个结果
        user_id: UUID | None = None,     # 按用户过滤（数据隔离）
    ) -> list[SearchResult]:
        raise NotImplementedError

    @abstractmethod
    async def delete_document(self, doc_id: UUID) -> None:  # 删除文档的所有向量
        raise NotImplementedError


# ---- ChromaDB 具体实现 ----
# ChromaDB：开源向量数据库，支持客户端-服务器模式和内存模式
class ChromaVectorStore(VectorStore):
    """ChromaDB 实现。优先连接远程服务，失败后降级到内存模式。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = None          # ChromaDB 客户端（懒加载）
        self._collection = None      # ChromaDB 集合（类似数据库的表）
        self.host = settings.chroma_host   # 服务器地址
        self.port = settings.chroma_port   # 服务器端口

    def _ensure_client(self) -> None:
        """确保客户端已连接。连接策略：远程优先 → 失败降级到内存模式。"""
        if self._client is not None:
            return  # 已连接，跳过

        # ===== 策略 1：连接远程 ChromaDB 服务器 =====
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            # HttpClient：通过 HTTP 协议连接远程服务器
            self._client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            # get_or_create_collection：有就用，没有就创建
            self._collection = self._client.get_or_create_collection(
                name="deepscribe_documents"
            )
            logger.info("chromadb_connected", host=self.host, port=self.port)
        except Exception:
            # ===== 策略 2：开发阶段降级到本地文件持久化模式 =====
            # 数据存磁盘（chroma_data/ 文件夹），重启不丢失
            import chromadb
            logger.warning("chromadb_fallback_to_local")
            self._client = chromadb.PersistentClient(path="./chroma_data")
            self._collection = self._client.get_or_create_collection(
                name="deepscribe_documents"
            )

    async def add_documents(
        self, doc_id: UUID, chunks: list[str], embeddings: list[list[float]],
    ) -> None:
        """将文档的文本块和向量批量存入 ChromaDB。"""
        self._ensure_client()
        # 为每块生成唯一 ID：格式 "文档UUID:序号"
        # enumerate 产生 (0, chunk0), (1, chunk1), ...
        ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
        # collection.add：批量添加数据
        self._collection.add(
            ids=ids,                                          # 块 ID 列表
            embeddings=embeddings,                            # 向量列表
            documents=chunks,                                 # 文本内容
            metadatas=[{"doc_id": str(doc_id)} for _ in chunks],  # 元数据
        )
        logger.info("chromadb_documents_added", doc_id=str(doc_id), chunk_count=len(chunks))

    async def search(
        self, query_embedding: list[float], top_k: int = 5, user_id: UUID | None = None,
    ) -> list[SearchResult]:
        """向量相似度搜索：给定一个查询向量，返回最相似的 top_k 个结果。"""
        self._ensure_client()
        # collection.query：执行向量搜索
        # query_embeddings 是二维数组（支持批量查询），这里只查一个
        # n_results：返回多少个结果
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        # ---- 解析 ChromaDB 返回的结果 ----
        search_results: list[SearchResult] = []
        # ChromaDB 返回结构：results["ids"][0] 是当前查询的 ID 列表
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                # 安全获取文本内容（防止字段不存在）
                content = results["documents"][0][i] if results["documents"] else ""
                # 获取距离值（ChromaDB 返回距离，越小越相似）
                distance = results["distances"][0][i] if results["distances"] else 1.0
                # 距离转相似度分数：距离 0 → 分数 1.0，距离 ≥1 → 分数 0.0
                score = 1.0 - min(distance, 1.0) if distance else 0.0
                search_results.append(SearchResult(chunk_id=chunk_id, content=content, score=score))

        return search_results

    async def delete_document(self, doc_id: UUID) -> None:
        """删除文档的所有向量（按 metadata 中的 doc_id 筛选删除）。"""
        self._ensure_client()
        # where={"doc_id": ...}：按元数据条件筛选删除
        self._collection.delete(where={"doc_id": str(doc_id)})
        logger.info("chromadb_document_deleted", doc_id=str(doc_id))
