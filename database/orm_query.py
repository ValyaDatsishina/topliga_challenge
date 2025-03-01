from typing import List, Tuple, Optional, Dict, Any, Callable, TypeVar, ParamSpec
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
import logging
from functools import wraps

from database.models import User, Result1, Telegram_ID, Promo

__all__ = [
    'DatabaseManager',
    'DatabaseException',
    'UserNotFoundError',
    'ResultNotFoundError',
    # Функции обратной совместимости
    'add_user',
    'get_users_all',
    'get_users_not_in_user',
    'get_users_not_in_result',
    'get_users_with_distance_1_no_distance_2',
    'get_users_with_distance_1_2_no_distance_3',
    'get_user_unique',
    'get_user_distances',
    'check_distances_filled',
    'get_total_distance',
    'get_promo_code',
    'get_user_results',
    'update_result1_for_user',
    'update_result2_for_user',
    'update_result3_for_user',
    'add_result_for_user',
    'get_user_login',
    'get_user_id'
]

logger = logging.getLogger(__name__)

# Типы для декоратора
P = ParamSpec('P')
T = TypeVar('T')

class DatabaseException(Exception):
    """Базовый класс для исключений базы данных"""
    pass

class UserNotFoundError(DatabaseException):
    """Исключение для случая, когда пользователь не найден"""
    pass

class ResultNotFoundError(DatabaseException):
    """Исключение для случая, когда результат не найден"""
    pass

class DatabaseManager:
    """
    Класс для управления операциями с базой данных.
    
    Пример использования:
        db = DatabaseManager(session)
        await db.add_user(user_data)
        distances = await db.get_user_distances(telegram_id)
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def _execute_query(self, query, error_message: str):
        """Выполняет запрос с обработкой ошибок"""
        try:
            result = await self.session.execute(query)
            return result
        except SQLAlchemyError as e:
            logger.error(f"{error_message}: {str(e)}")
            raise DatabaseException(error_message)
    
    async def add_user(self, data: Dict[str, Any]) -> None:
        """Добавляет нового пользователя"""
        try:
            # Создаем пользователя
            user = User(
                telegram_id=data['telegram_id'],
                telegram_login=data['telegram_login'],
                name=data['name'],
                phone=data['phone'],
                email=data['email'],
                date_reg=data['date_reg']
            )
            
            # Проверяем существование telegram_id
            query = select(Telegram_ID).filter_by(telegram_id=data['telegram_id'])
            result = await self._execute_query(query, "Ошибка при проверке telegram_id")
            
            if not result.scalars().first():
                telegram_id = Telegram_ID(telegram_id=data['telegram_id'])
                self.session.add(telegram_id)
            
            self.session.add(user)
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при добавлении пользователя: {str(e)}")
            raise
    
    async def get_users_all(self) -> List[int]:
        """Получает все Telegram ID пользователей"""
        query = select(Telegram_ID.telegram_id)
        result = await self._execute_query(query, "Ошибка при получении пользователей")
        return [row[0] for row in result.fetchall()]
    
    async def get_users_not_registered(self) -> List[int]:
        """Получает Telegram ID незарегистрированных пользователей"""
        query = (
            select(Telegram_ID.telegram_id)
            .outerjoin(User, Telegram_ID.telegram_id == User.telegram_id)
            .where(User.telegram_id.is_(None))
        )
        result = await self._execute_query(query, "Ошибка при получении незарегистрированных пользователей")
        return [row[0] for row in result.fetchall()]
    
    async def get_users_without_first_day(self) -> List[int]:
        """Получает пользователей без результатов первого дня"""
        query = (
            select(User.telegram_id)
            .outerjoin(Result1, User.id == Result1.user_id)
            .where(Result1.user_id.is_(None))
        )
        result = await self._execute_query(query, "Ошибка при получении пользователей без первого дня")
        return [row[0] for row in result.fetchall()]
    
    async def get_users_with_incomplete_results(self, day: int) -> List[int]:
        """Получает пользователей с неполными результатами"""
        conditions = {
            1: and_(Result1.distance_1.isnot(None), Result1.distance_2.is_(None)),
            2: and_(
                Result1.distance_1.isnot(None),
                Result1.distance_2.isnot(None),
                Result1.distance_3.is_(None)
            )
        }
        
        if day not in conditions:
            raise ValueError(f"Неверный день: {day}")
        
        query = (
            select(User.telegram_id)
            .join(Result1, User.id == Result1.user_id)
            .where(conditions[day])
        )
        
        result = await self._execute_query(query, f"Ошибка при получении пользователей с неполными результатами дня {day}")
        return [row[0] for row in result.fetchall()]
    
    def _get_user_unique_sync(self, telegram_id: int) -> bool:
        """Синхронная версия проверки существования пользователя для кэширования"""
        return telegram_id in self._user_cache

    @property
    def _user_cache(self) -> set:
        """Кэш для хранения telegram_id пользователей"""
        if not hasattr(self, '_user_id_cache'):
            self._user_id_cache = set()
        return self._user_id_cache

    async def get_user_unique(self, telegram_id: int) -> bool:
        """Проверяет существование пользователя"""
        # Проверяем кэш
        if telegram_id in self._user_cache:
            return True
            
        # Если нет в кэше, проверяем базу
        query = select(func.count(User.telegram_id)).where(User.telegram_id == telegram_id)
        result = await self._execute_query(query, "Ошибка при проверке пользователя")
        exists = bool(result.scalar())
        
        # Если пользователь существует, добавляем в кэш
        if exists:
            self._user_cache.add(telegram_id)
            
        return exists
    
    async def get_user_distances(self, telegram_id: int) -> Tuple[float, float, float]:
        """
        Получает дистанции пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Tuple[float, float, float]: Кортеж с дистанциями за три дня
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            DatabaseException: При ошибках работы с базой данных
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self.get_user_unique(telegram_id)
            if not user_exists:
                raise UserNotFoundError(f"Пользователь не найден: {telegram_id}")
            
            # Получаем результаты
            query = (
                select(Result1)
                .join(User)
                .where(User.telegram_id == telegram_id)
                .options(selectinload(Result1.user))
            )
            result = await self._execute_query(query, "Ошибка при получении дистанций")
            distances = result.scalars().first()
            
            if not distances:
                logger.info(f"Результаты не найдены для пользователя {telegram_id}")
                return 0.0, 0.0, 0.0
            
            # Преобразуем None в 0.0 и проверяем типы
            return (
                float(distances.distance_1 or 0.0),
                float(distances.distance_2 or 0.0),
                float(distances.distance_3 or 0.0)
            )
            
        except UserNotFoundError:
            raise
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка преобразования данных для пользователя {telegram_id}: {e}")
            return 0.0, 0.0, 0.0
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении дистанций для пользователя {telegram_id}: {e}")
            raise DatabaseException(f"Ошибка при получении дистанций: {e}")
    
    async def check_distances_filled(self, telegram_id: int) -> bool:
        """
        Проверяет заполнение всех дистанций
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если все дистанции заполнены, False иначе
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            DatabaseException: При ошибках работы с базой данных
        """
        try:
            distances = await self.get_user_distances(telegram_id)
            return all(isinstance(d, (int, float)) and d > 0 for d in distances)
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Ошибка при проверке дистанций для пользователя {telegram_id}: {e}")
            raise DatabaseException(f"Ошибка при проверке дистанций: {e}")
    
    async def get_total_distance(self, telegram_id: int) -> float:
        """
        Получает общую дистанцию пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            float: Общая дистанция
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            DatabaseException: При ошибках работы с базой данных
        """
        try:
            # Проверяем существование пользователя
            user_exists = await self.get_user_unique(telegram_id)
            if not user_exists:
                raise UserNotFoundError(f"Пользователь не найден: {telegram_id}")
            
            # Получаем сумму дистанций
            query = (
                select(
                    func.coalesce(func.sum(Result1.distance_1), 0.0) +
                    func.coalesce(func.sum(Result1.distance_2), 0.0) +
                    func.coalesce(func.sum(Result1.distance_3), 0.0)
                )
                .join(User)
                .filter(User.telegram_id == telegram_id)
            )
            
            result = await self._execute_query(query, "Ошибка при подсчете общей дистанции")
            total = result.scalar()
            
            # Проверяем и преобразуем результат
            if total is None:
                logger.info(f"Нет результатов для пользователя {telegram_id}")
                return 0.0
                
            try:
                return float(total)
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка преобразования общей дистанции для пользователя {telegram_id}: {e}")
                return 0.0
                
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при подсчете общей дистанции для пользователя {telegram_id}: {e}")
            raise DatabaseException(f"Ошибка при подсчете общей дистанции: {e}")
    
    async def get_promo_code(self, telegram_id: int) -> str:
        """Получает промокод пользователя"""
        query = (
            select(Promo)
            .join(Result1)
            .join(User)
            .filter(User.telegram_id == telegram_id)
        )
        
        result = await self._execute_query(query, "Ошибка при получении промокода")
        promo = result.scalars().first()
        
        if not promo:
            return "Промокод не найден"
        
        return promo.Code
    
    async def get_user_results(self, telegram_id: int) -> Optional[Tuple[User, Result1]]:
        """Получает результаты пользователя"""
        query = (
            select(User, Result1)
            .join(Result1)
            .filter(User.telegram_id == telegram_id)
            .options(selectinload(User.results))
        )
        
        result = await self._execute_query(query, "Ошибка при получении результатов")
        return result.first()
    
    async def update_result(self, telegram_id: int, data: Dict[str, Any], day: int) -> None:
        """Обновляет результаты пользователя"""
        try:
            # Получаем пользователя
            user_query = select(User).filter(User.telegram_id == telegram_id)
            user_result = await self._execute_query(user_query, "Ошибка при получении пользователя")
            user = user_result.scalars().first()
            
            if not user:
                raise UserNotFoundError(f"Пользователь не найден: {telegram_id}")
            
            # Получаем или создаем результат
            result_query = select(Result1).filter(Result1.user_id == user.id)
            result = await self._execute_query(result_query, "Ошибка при получении результата")
            result = result.scalars().first()
            
            if not result:
                result = Result1(user_id=user.id)
                self.session.add(result)
            
            # Обновляем данные
            distance = float(data.get('distance', 0))
            photo = data.get(f'photo_{day}')
            story = data.get(f'story_{day}')
            date = data.get(f'date_{day}')
            
            setattr(result, f'distance_{day}', distance)
            setattr(result, f'photo_{day}', photo)
            setattr(result, f'story_{day}', story)
            setattr(result, f'date_{day}', date)
            
            if day == 3:
                result.result = await self.get_total_distance(telegram_id) + distance
            
            await self.session.commit()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при обновлении результата: {str(e)}")
            raise

    async def add_result_for_user(self, telegram_id: int, data: Dict[str, Any], day: int) -> None:
        """
        Добавляет или обновляет результат пользователя за определенный день
        
        Args:
            telegram_id: ID пользователя в Telegram
            data: Данные результата (distance, photo, story, date)
            day: Номер дня (1-3)
            
        Raises:
            UserNotFoundError: Если пользователь не найден
            ValueError: Если указан неверный день
            DatabaseException: При ошибках работы с базой данных
        """
        try:
            if day not in [1, 2, 3]:
                raise ValueError(f"Неверный день: {day}")

            # Получаем пользователя
            query = select(User).where(User.telegram_id == telegram_id)
            result = await self._execute_query(query, "Ошибка при получении пользователя")
            user = result.scalars().first()
            
            if not user:
                raise UserNotFoundError(f"Пользователь не найден: {telegram_id}")
            
            # Получаем или создаем запись результата
            result_query = select(Result1).where(Result1.user_id == user.id)
            result = await self._execute_query(result_query, "Ошибка при получении результата")
            result_record = result.scalars().first()
            
            if not result_record:
                result_record = Result1(user_id=user.id)
                self.session.add(result_record)
            
            # Обновляем данные
            distance = float(data.get('distance', 0))
            photo = data.get('photo')
            story = data.get('story')
            date = data.get('date')
            
            setattr(result_record, f'distance_{day}', distance)
            setattr(result_record, f'photo_{day}', photo)
            setattr(result_record, f'story_{day}', story)
            setattr(result_record, f'date_{day}', date)
            
            # Обновляем общий результат если это последний день
            if day == 3:
                total_distance = await self.get_total_distance(telegram_id)
                result_record.result = total_distance + distance
            
            await self.session.commit()
            logger.info(f"Результат за день {day} успешно добавлен для пользователя {telegram_id}")
            
        except (ValueError, TypeError) as e:
            await self.session.rollback()
            logger.error(f"Ошибка в данных при добавлении результата: {e}")
            raise ValueError(f"Ошибка в данных результата: {e}")
        except UserNotFoundError:
            await self.session.rollback()
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при добавлении результата: {e}")
            raise DatabaseException(f"Ошибка при добавлении результата: {e}")

    async def get_user_login(self, telegram_login: str) -> Optional[User]:
        """
        Получает пользователя по его логину в Telegram
        
        Args:
            telegram_login: Логин пользователя в Telegram
            
        Returns:
            Optional[User]: Объект пользователя или None, если не найден
        """
        try:
            query = select(User).where(User.telegram_login == telegram_login)
            result = await self.session.execute(query)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении пользователя по логину {telegram_login}: {e}")
            raise DatabaseException(f"Ошибка при получении пользователя: {e}")

    async def get_user_id(self, result_id: int) -> Optional[Tuple[User, Result1]]:
        """
        Получает пользователя и его результаты по ID результата
        
        Args:
            result_id: ID записи результата
            
        Returns:
            Optional[Tuple[User, Result1]]: Кортеж с пользователем и его результатами или None
        """
        try:
            query = (
                select(User, Result1)
                .join(Result1)
                .filter(Result1.id == result_id)
                .options(selectinload(User.results))
            )
            result = await self._execute_query(query, "Ошибка при получении пользователя по ID результата")
            return result.first()
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении пользователя по ID результата {result_id}: {e}")
            raise DatabaseException(f"Ошибка при получении пользователя: {e}")

def with_db_manager(func: Callable[Tuple[DatabaseManager, P], T]) -> Callable[Tuple[AsyncSession, P], T]:
    """Декоратор для создания функций обратной совместимости"""
    @wraps(func)
    async def wrapper(session: AsyncSession, *args: P.args, **kwargs: P.kwargs) -> T:
        db = DatabaseManager(session)
        return await func(db, *args, **kwargs)
    return wrapper

# Функции обратной совместимости
@with_db_manager
async def add_user(db: DatabaseManager, data: Dict[str, Any]) -> None:
    return await db.add_user(data)

@with_db_manager
async def get_users_all(db: DatabaseManager) -> List[int]:
    return await db.get_users_all()

@with_db_manager
async def get_users_not_in_user(db: DatabaseManager) -> List[int]:
    return await db.get_users_not_registered()

@with_db_manager
async def get_users_not_in_result(db: DatabaseManager) -> List[int]:
    return await db.get_users_without_first_day()

@with_db_manager
async def get_users_with_distance_1_no_distance_2(db: DatabaseManager) -> List[int]:
    return await db.get_users_with_incomplete_results(1)

@with_db_manager
async def get_users_with_distance_1_2_no_distance_3(db: DatabaseManager) -> List[int]:
    return await db.get_users_with_incomplete_results(2)

@with_db_manager
async def get_user_unique(db: DatabaseManager, telegram_id: int) -> bool:
    return await db.get_user_unique(telegram_id)

@with_db_manager
async def get_user_distances(db: DatabaseManager, telegram_id: int) -> Tuple[float, float, float]:
    return await db.get_user_distances(telegram_id)

@with_db_manager
async def check_distances_filled(db: DatabaseManager, telegram_id: int) -> bool:
    return await db.check_distances_filled(telegram_id)

@with_db_manager
async def get_total_distance(db: DatabaseManager, telegram_id: int) -> float:
    return await db.get_total_distance(telegram_id)

@with_db_manager
async def get_promo_code(db: DatabaseManager, telegram_id: int) -> str:
    return await db.get_promo_code(telegram_id)

@with_db_manager
async def get_user_results(db: DatabaseManager, telegram_id: int) -> Optional[Tuple[User, Result1]]:
    return await db.get_user_results(telegram_id)

@with_db_manager
async def update_result1_for_user(db: DatabaseManager, telegram_id: int, data: Dict[str, Any]) -> None:
    return await db.update_result(telegram_id, data, 1)

@with_db_manager
async def update_result2_for_user(db: DatabaseManager, telegram_id: int, data: Dict[str, Any]) -> None:
    return await db.update_result(telegram_id, data, 2)

@with_db_manager
async def update_result3_for_user(db: DatabaseManager, telegram_id: int, data: Dict[str, Any]) -> None:
    return await db.update_result(telegram_id, data, 3)

@with_db_manager
async def add_result_for_user(db: DatabaseManager, telegram_id: int, data: Dict[str, Any], day: int) -> None:
    return await db.add_result_for_user(telegram_id, data, day)

@with_db_manager
async def get_user_login(db: DatabaseManager, telegram_login: str) -> Optional[User]:
    return await db.get_user_login(telegram_login)

@with_db_manager
async def get_user_id(db: DatabaseManager, result_id: int) -> Optional[Tuple[User, Result1]]:
    return await db.get_user_id(result_id)
