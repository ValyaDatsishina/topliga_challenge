from typing import Any, Awaitable, Callable, Dict, Optional, AsyncGenerator, AsyncContextManager
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Базовое исключение для ошибок базы данных в middleware"""
    pass

class DataBaseSession(BaseMiddleware):
    """Middleware для управления сессией базы данных"""
    
    def __init__(self, session_pool: async_sessionmaker) -> None:
        """
        Инициализация middleware
        
        Args:
            session_pool: Фабрика сессий SQLAlchemy
        """
        super().__init__()
        self.session_pool = session_pool
    
    @asynccontextmanager
    async def _get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Контекстный менеджер для получения сессии
        
        Yields:
            AsyncSession: Сессия базы данных
            
        Raises:
            DatabaseError: При ошибках работы с базой данных
        """
        session = self.session_pool()
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Ошибка базы данных: {e}")
            raise DatabaseError(f"Ошибка при работе с базой данных: {e}")
        finally:
            await session.close()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработчик middleware
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие Telegram
            data: Данные события
            
        Returns:
            Any: Результат обработки события
            
        Raises:
            DatabaseError: При ошибках работы с базой данных
        """
        try:
            async with self._get_session() as session:
                data['session'] = session
                return await handler(event, data)
        except DatabaseError:
            # Логирование уже выполнено в _get_session
            raise
        except Exception as e:
            logger.error(f"Необработанная ошибка в middleware: {e}")
            raise
