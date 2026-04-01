from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings

def _build_url() -> str:
    url = settings.DATABASE_URL
    # asyncpg on Windows: 한글 사용자 경로에서 SSL cert 로드 실패 방지
    if "?" not in url:
        url += "?ssl=disable"
    elif "ssl=" not in url:
        url += "&ssl=disable"
    return url


engine = create_async_engine(
    _build_url(),
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def check_db_connection() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def ensure_postgis() -> None:
    """PostGIS 확장이 활성화되어 있는지 확인하고, 없으면 생성한다."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
