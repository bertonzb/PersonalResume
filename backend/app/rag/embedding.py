from __future__ import annotations

from app.config import get_settings


class EmbeddingService:
    """文档 Embedding 服务，封装 OpenAI Embeddings API。"""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key)
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量。"""
        if not self.api_key:
            # 无 API Key 时返回零向量（开发调试用）
            return [[0.0] * 1536 for _ in texts]

        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    async def embed_query(self, query: str) -> list[float]:
        """将查询文本转换为单个向量。"""
        results = await self.embed_texts([query])
        return results[0]
