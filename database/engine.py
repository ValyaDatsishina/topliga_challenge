import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database.models import Base

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:password_topliga@db:5432/db_challenge')

# Создаем движок с отключенным пулом соединений для Docker
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool  # Отключаем пул соединений для Docker
)

session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False  # Отключаем автоматический flush для лучшей производительности
)

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def get_session() -> AsyncSession:
    """Создает новую сессию базы данных"""
    async with session_maker() as session:
        yield session
