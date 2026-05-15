# =============================================================================
# 文件：app/core/database.py
# 作用：SQL Server 异步数据库引擎和会话管理。
# 解释：使用 aioodbc（异步 ODBC 驱动）+ SQLAlchemy 2.0 异步 API，
#       提供 async engine、async session factory、以及 FastAPI 依赖注入。
# =============================================================================
from __future__ import annotations

from collections.abc import AsyncGenerator

# create_async_engine：创建异步数据库引擎
# async_sessionmaker：创建异步会话的工厂函数
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


# ---- 创建异步引擎 ----
# echo=False：不打印 SQL 日志（设 True 可在控制台看到每条 SQL）
# pool_size=10：连接池默认保持 10 条连接
# max_overflow=20：连接池满了后最多再创建 20 条临时连接
_engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

# ---- 创建异步会话工厂 ----
# expire_on_commit=False：提交后不使对象过期（否则提交后访问属性会报错）
AsyncSessionLocal = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ---- FastAPI 依赖注入 ----
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（FastAPI 依赖注入用）。

    用法：
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(...)

    每个请求获取一个独立的会话，请求结束后自动关闭。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """初始化数据库：创建所有 ORM 模型对应的表（开发用）。

    生产环境应使用 Alembic 迁移。
    """
    from app.models.base import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库引擎，释放连接池。"""
    await _engine.dispose()
