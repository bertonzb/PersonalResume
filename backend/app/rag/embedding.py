# =============================================================================
# 文件：app/rag/embedding.py
# 作用：Embedding（向量化）服务。把文字变成一串数字（向量），用于语义搜索。
#       通俗理解：给文字一个"坐标"，含义相近的文字坐标也近。
# =============================================================================
from __future__ import annotations
from app.config import get_settings
from app.core.logging import logger


class EmbeddingService:
    """文档 Embedding 服务，使用 LLM 服务商提供的 Embeddings API。

    什么是 Embedding？把 "猫" → [0.1, 0.3, -0.2, ...]
    语义相近的词，向量也相近（"猫"和"猫咪"的向量距离很近）。
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        """初始化。参数不传则从配置文件读取。"""
        settings = get_settings()
        # API 密钥：优先用传入的，否则用配置文件的
        self.api_key = api_key or settings.llm_api_key
        # base_url：兼容任何 OpenAI 格式的 API（OpenAI/DeepSeek/Ollama）
        self.base_url = settings.llm_base_url
        # 模型名称（如 text-embedding-3-small）
        self.model = model or settings.embedding_model
        # _client：OpenAI 客户端，None 表示还没创建（懒加载）
        self._client = None

    # @property：把方法变成属性，调用时不用加括号（self.client 而不是 self.client()）
    @property
    def client(self):
        """懒加载获取 OpenAI 客户端。第一次访问时才创建连接。"""
        if self._client is None:
            # OpenAI 官方 Python SDK
            from openai import OpenAI

            # 创建客户端，base_url 支持切换到任何兼容 OpenAI 格式的服务
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量把文本列表转成向量。async 是因为调用外部 API 是网络操作。"""
        if not self.api_key:
            # 无 API Key 时返回零向量，保证开发阶段能跑通流程
            # 1536 是 OpenAI text-embedding-ada-002 的输出维度
            # _ 是 Python 惯例：不需要用到的循环变量用 _ 占位
            return [[0.0] * 1536 for _ in texts]

        try:
            # 调用 Embedding API（一次传多条文本，节省网络开销）
            response = self.client.embeddings.create(model=self.model, input=texts)
            # response.data 是结果列表，每个 item.embedding 就是向量
            return [item.embedding for item in response.data]
        except Exception as e:
            # API 调用失败时记录警告，返回零向量作为降级方案
            logger.warning("embedding_failed_using_zero_vectors", error=str(e))
            return [[0.0] * 1536 for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        """把查询文本转成单个向量（内部调用 embed_texts）。"""
        results = await self.embed_texts([query])
        return results[0]  # 只取第一个（只有一个查询）
