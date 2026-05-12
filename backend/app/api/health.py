from __future__ import annotations

from fastapi import APIRouter

from app.core.logging import logger

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查接口。"""
    logger.info("health_check")
    return {"status": "ok", "version": "0.1.0"}
