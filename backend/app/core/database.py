import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Database file lives in backend/data/watchdog.db
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR / 'watchdog.db'}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
