# =============================================================================
# 文件：app/core/llm_provider.py
# 作用：LLM 提供器——统一抽象，支持 API / vLLM / SGLang 三种推理模式切换。
#       当前 ChatOpenAI 兼容三种模式（都支持 OpenAI 格式的 /v1 端点）。
#       后续可针对 vLLM/SGLang 特性做专项优化（如 continuous batching、prefix caching）。
# =============================================================================
"""
LLM 推理模式切换指南
====================

模式 1 —— API 模式（当前使用）：
    在 .env 中设置：
        LLM_MODE=api
        LLM_BASE_URL=https://api.deepseek.com/v1
        LLM_MODEL=deepseek-chat

模式 2 —— vLLM 本地推理（高性能）：
    1. 部署 vLLM：
        pip install vllm
        python -m vllm.entrypoints.openai.api_server \
            --model Qwen/Qwen2.5-7B-Instruct \
            --tensor-parallel-size 1 \
            --max-model-len 8192 \
            --port 8100
    2. 在 .env 中设置：
        LLM_MODE=vllm
        LLM_LOCAL_URL=http://localhost:8100/v1
        LLM_LOCAL_MODEL=Qwen/Qwen2.5-7B-Instruct

模式 3 —— SGLang 本地推理（高吞吐）：
    1. 部署 SGLang：
        pip install sglang[all]
        python -m sglang.launch_server \
            --model Qwen/Qwen2.5-7B-Instruct \
            --port 8200
    2. 在 .env 中设置：
        LLM_MODE=sglang
        LLM_LOCAL_URL=http://localhost:8200/v1
        LLM_LOCAL_MODEL=Qwen/Qwen2.5-7B-Instruct

vLLM vs SGLang 选型参考：
    vLLM： 社区更大、稳定性好、适合一般生产场景
    SGLang：RadixAttention 前缀缓存、更高吞吐、适合高并发场景
"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.core.logging import logger


class LLMProvider:
    """LLM 提供器——根据配置切换 API / vLLM / SGLang。

    三种模式底层都用 ChatOpenAI（因为 vLLM 和 SGLang 都暴露 /v1 端点），
    仅 base_url 和 model 参数不同。后续可为 vLLM/SGLang 添加专项参数。
    """

    @staticmethod
    def create() -> ChatOpenAI:
        """根据配置创建 LLM 实例。

        返回的 ChatOpenAI 可用于 LangChain Agent 或直接 ainvoke()。
        """
        settings = get_settings()
        mode = settings.llm_mode

        if mode == "vllm":
            return LLMProvider._create_vllm(settings)
        elif mode == "sglang":
            return LLMProvider._create_sglang(settings)
        else:
            return LLMProvider._create_api(settings)

    @staticmethod
    def _create_api(settings) -> ChatOpenAI:
        """API 模式：连接 OpenAI / DeepSeek 等云端服务。"""
        logger.info("llm_provider", mode="api", url=settings.llm_base_url)
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.1,
        )

    @staticmethod
    def _create_vllm(settings) -> ChatOpenAI:
        """vLLM 模式：连接本地 vLLM 推理服务。

        vLLM 特性（后续可专项利用）：
        - Continuous batching：自动合并请求批次，提升 GPU 利用率
        - PagedAttention：KV cache 分页管理，降低显存占用
        - Tensor parallelism：多 GPU 并行推理
        """
        logger.info("llm_provider", mode="vllm", url=settings.llm_local_url)
        return ChatOpenAI(
            model=settings.llm_local_model,
            api_key="not-needed",  # vLLM 本地部署无需 API Key
            base_url=settings.llm_local_url,
            temperature=0.1,
            # vLLM 专项参数（通过 model_kwargs 透传）
            model_kwargs={
                # "max_tokens": 2048,          # 最大生成长度
                # "stop": ["<|endoftext|>"],   # 停止词
            },
        )

    @staticmethod
    def _create_sglang(settings) -> ChatOpenAI:
        """SGLang 模式：连接本地 SGLang 推理服务。

        SGLang 特性（后续可专项利用）：
        - RadixAttention：前缀缓存，共享相同前缀的请求速度提升 5x
        - 高吞吐调度：适合大规模并发场景
        - 结构化输出：原生支持 JSON mode / constrained decoding
        """
        logger.info("llm_provider", mode="sglang", url=settings.llm_local_url)
        return ChatOpenAI(
            model=settings.llm_local_model,
            api_key="not-needed",  # SGLang 本地部署无需 API Key
            base_url=settings.llm_local_url,
            temperature=0.1,
            model_kwargs={
                # "max_tokens": 2048,
            },
        )
