# 启用"延迟求值"类型注解
from __future__ import annotations

# uuid：生成全局唯一 ID（TraceID 就是一个 UUID）
import uuid

# structlog：结构化日志
import structlog
# Request：FastAPI（Starlette）的请求对象，包含请求头、URL 等
from fastapi import Request
# BaseHTTPMiddleware：Starlette 的 HTTP 中间件基类
# 中间件 = 请求处理流水线上的"关卡"，每个请求都会经过它
from starlette.middleware.base import BaseHTTPMiddleware
# Response：HTTP 响应对象
from starlette.responses import Response

# 获取日志器实例
logger = structlog.get_logger()


# ---- TraceID 中间件 ----
# 什么是 TraceID？
# 用户发一个请求 → API 层 → Service 层 → Agent 层 → LLM 调用
# 每一层都会记录日志，但怎么知道哪些日志属于同一次请求？
# 答案：给每条日志打上相同的 trace_id 标签，搜索时就嫩找到完整的请求链路

# 什么是中间件？
# FastAPI 的请求处理流程：
#   请求进入 → 中间件1 → 中间件2 → 路由处理函数 → 返回响应
# 中间件可以：
#   1. 在请求到达处理函数之前做一些事（如注入 trace_id）
#   2. 在响应返回之前做一些事（如添加响应头）
class TraceIDMiddleware(BaseHTTPMiddleware):
    """TraceID 中间件：为每个请求注入 trace_id 到 structlog 上下文。"""

    # dispatch 方法：每个 HTTP 请求都会经过这个方法
    # request：当前请求对象
    # call_next：调用下一个中间件（或路由处理函数）
    async def dispatch(self, request: Request, call_next):
        # ---- 步骤 1：获取或生成 TraceID ----
        # 优先从请求头中读取（如果前端发请求时带了 X-Trace-ID），
        # 没有则用 uuid4 自动生成一个新的
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

        # ---- 步骤 2：注入到 structlog 上下文 ----
        # bind_contextvars：把 trace_id 绑定到当前请求的日志上下文中
        # 之后这个请求里所有的 logger.info()/error() 输出都会自动带上 trace_id
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        # ---- 步骤 3：继续处理请求 ----
        # call_next(request)：把请求传给下一个中间件或路由处理函数
        # 返回的是处理完成的 Response 对象
        response: Response = await call_next(request)

        # ---- 步骤 4：在响应头中附加 TraceID ----
        # 把 trace_id 加到 HTTP 响应头，前端可以读取
        # 这样前后端都用同一个 trace_id，排查问题时更方便
        response.headers["X-Trace-ID"] = trace_id

        # ---- 步骤 5：清理上下文 ----
        # 请求结束后解绑 trace_id，避免影响下一个请求
        structlog.contextvars.unbind_contextvars("trace_id")

        return response
