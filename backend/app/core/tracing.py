from __future__ import annotations

import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger()


class TraceIDMiddleware(BaseHTTPMiddleware):
    """TraceID 中间件：为每个请求注入 trace_id 到 structlog 上下文。"""

    async def dispatch(self, request: Request, call_next):
        # 从请求头获取或生成 trace_id
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

        # 注入到 structlog 上下文
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        # 处理请求
        response: Response = await call_next(request)

        # 响应头附加 trace_id
        response.headers["X-Trace-ID"] = trace_id

        # 清理上下文
        structlog.contextvars.unbind_contextvars("trace_id")

        return response
