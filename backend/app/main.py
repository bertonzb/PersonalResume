from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.core.exceptions import AppException
from app.core.logging import logger, setup_logging
from app.core.tracing import TraceIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    setup_logging()
    logger.info("app_startup")
    yield
    logger.info("app_shutdown")


app = FastAPI(
    title="DeepScribe API",
    description="个人知识库深度研究助手",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TraceID 中间件（在 CORS 之后）
app.add_middleware(TraceIDMiddleware)


# ---- 全局异常处理器 ----

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    status_map = {
        "NOT_FOUND": 404,
        "PERMISSION_DENIED": 403,
    }
    status_code = status_map.get(exc.code, 500)
    trace_id = structlog.contextvars.get_contextvars().get("trace_id", "")
    logger.error(
        "app_exception",
        code=exc.code,
        message=exc.message,
        status_code=status_code,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "trace_id": str(trace_id),
        },
    )


# 注册路由
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
