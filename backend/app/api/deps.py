from collections.abc import AsyncGenerator

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class CommonQueryParams:
    def __init__(
        self,
        skip: int = Query(default=0, ge=0, description="跳过的记录数"),
        limit: int = Query(default=20, ge=1, le=100, description="每页返回的记录数"),
        keyword: str | None = Query(default=None, description="搜索关键词"),
    ) -> None:
        self.skip = skip
        self.limit = limit
        self.keyword = keyword
