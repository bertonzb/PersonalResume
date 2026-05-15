# =============================================================================
# 文件：app/api/health.py
# 作用：健康检查接口。最简单的 API 示例，验证后端服务是否正常运行。
#       访问 http://localhost:8000/api/v1/health 即可测试。
# =============================================================================

from __future__ import annotations

# APIRouter：FastAPI 的路由器，用来组织和管理一组相关的 API 接口
from fastapi import APIRouter
from app.core.logging import logger

# 创建路由器实例
# tags=["health"]：在 Swagger 文档中，这个路由器的接口会被分组到 "health" 标签下
router = APIRouter(tags=["health"])


# @router.get("/health")：注册一个 GET 请求的路由
# 当有人访问 http://localhost:8000/api/v1/health 时，调用下面这个函数
# async def：异步函数，可以同时处理多个请求
# dict[str, str]：返回值类型提示，返回一个字典，键和值都是字符串
@router.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查接口。"""
    # 记录一条日志
    logger.info("health_check")
    # 返回 JSON 格式的响应
    # FastAPI 会自动把 Python 字典转成 JSON 字符串发给前端
    return {"status": "ok", "version": "0.1.0"}
