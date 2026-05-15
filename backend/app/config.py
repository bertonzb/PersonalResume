# 启用"延迟求值"类型注解（Python 3.10+ 特性）
from __future__ import annotations

# os：操作系统相关功能（当前暂未直接使用，保留以备扩展）
import os
# lru_cache：缓存函数返回值，避免重复创建 Settings 对象
from functools import lru_cache

# pydantic-settings：专门用来管理配置的库
# BaseSettings：配置基类，自动从 .env 文件和环境变量读取配置
# SettingsConfigDict：配置类的行为设置
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---- 应用配置类 ----
# 这是整个项目的"配置中心"，所有可配置项都定义在这里
# 启动时从项目根目录的 .env 文件自动加载
class Settings(BaseSettings):
    """应用配置，从 .env 文件和环境变量读取。"""

    # model_config：告诉 Pydantic 如何加载配置
    # env_file 支持多个路径：优先找 backend/.env，再找 ../.env（项目根目录）
    # 这样无论从哪个目录启动都能正确加载
    # extra="ignore"：.env 中有但未定义的字段会被忽略（不报错）
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========== 应用基础配置 ==========
    # app_env：运行环境（development / production）
    app_env: str = "development"
    # log_level：日志级别（DEBUG / INFO / WARNING / ERROR）
    log_level: str = "INFO"
    # backend_port：后端服务监听的端口号
    backend_port: int = 8000

    # ========== 数据库配置 ==========
    # database_url：数据库连接字符串
    # SQL Server 格式（aioodbc）：
    #   mssql+aioodbc://用户名:密码@主机:端口/数据库名?odbc_connect=编码后的ODBC连接串
    #
    # ODBC 连接串通过 odbc_connect 参数透传，支持命名实例（如 SERVER\INSTANCE）
    # 需安装 ODBC Driver 17 for SQL Server：
    #   https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
    database_url: str = (
        "mssql+aioodbc://myDeepScribe:qaz123WSX@localhost:1433/DeepScribe"
        "?odbc_connect=DRIVER%3D%7BODBC+Driver+17+for+SQL+Server%7D%3B"
        "SERVER%3DBERTON%5CMYDATABASE%3B"
        "DATABASE%3DDeepScribe%3B"
        "UID%3DmyDeepScribe%3B"
        "PWD%3Dqaz123WSX%3B"
        "TrustServerCertificate%3Dyes%3B"
    )

    # ========== Redis 配置 ==========
    # Redis：内存缓存数据库，用于 Celery 任务队列和缓存
    # 格式：redis://主机:端口/数据库编号
    redis_url: str = "redis://localhost:6379/0"

    # ========== ChromaDB 配置 ==========
    # ChromaDB：向量数据库，存储文档的"向量"用于语义搜索
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # ========== LLM 推理模式 ==========
    # "api"：调用云端 API（OpenAI/DeepSeek 等）
    # "vllm"：使用 vLLM 本地推理引擎（高性能，需独立部署）
    # "sglang"：使用 SGLang 本地推理引擎（高吞吐，需独立部署）
    llm_mode: str = "api"

    # ========== API 模式（llm_mode="api" 时生效）==========
    # 兼容 OpenAI、DeepSeek 等任何 OpenAI 格式的 API
    llm_api_key: str = ""
    # llm_base_url：API 地址
    #   OpenAI 用户：https://api.openai.com/v1
    #   DeepSeek 用户：https://api.deepseek.com/v1
    llm_base_url: str = "https://api.openai.com/v1"
    # llm_model：使用的模型名称
    #   OpenAI：gpt-4o / gpt-3.5-turbo
    #   DeepSeek：deepseek-chat
    llm_model: str = "gpt-4o"

    # ========== vLLM / SGLang 本地推理引擎（llm_mode="vllm"/"sglang" 时生效）==========
    # vLLM：https://github.com/vllm-project/vllm
    # SGLang：https://github.com/sgl-project/sglang
    # 部署命令示例：
    #   vLLM：  python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-7B-Instruct --port 8100
    #   SGLang：python -m sglang.launch_server --model Qwen/Qwen2.5-7B-Instruct --port 8200
    llm_local_url: str = "http://localhost:8100/v1"
    llm_local_model: str = "Qwen/Qwen2.5-7B-Instruct"

    # ========== AI — Embedding 向量化 ==========
    embedding_model: str = "text-embedding-3-small"

    # ========== JWT 鉴权配置 ==========
    # JWT（JSON Web Token）：登录后返回给前端的加密凭证
    # jwt_secret：签名密钥（生产环境必须换成随机字符串！）
    jwt_secret: str = "dev-secret-change-in-production"
    # jwt_algorithm：加密算法，HS256 是对称加密
    jwt_algorithm: str = "HS256"
    # jwt_expire_minutes：Token 有效期（分钟），1440 = 24 小时
    jwt_expire_minutes: int = 1440

    # ========== API Key 加密配置 ==========
    # encryption_key：用于加密用户存储的第三方 API Key
    # 使用 AES-GCM 加密（通过 cryptography 库的 Fernet）
    encryption_key: str = "dev-encryption-key-32bytes!!!"

    # ========== 搜索服务配置 ==========
    # tavily_api_key：联网搜索 Tool 使用的 API Key（可选）
    tavily_api_key: str = ""


# ---- 全局配置获取函数 ----
# @lru_cache：只创建一次 Settings 实例，后续调用返回缓存的结果
# 这保证整个应用使用同一份配置，且不会重复读取 .env 文件
@lru_cache
def get_settings() -> Settings:
    """获取全局唯一的 Settings 实例（带缓存）。"""
    return Settings()
