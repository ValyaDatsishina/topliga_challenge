from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database.models import User, Result, Telegram_ID

"""Добавление в бд нового участника"""


async def add_user(session: AsyncSession, data: dict):
    obj = User(
        telegram_id=data['telegram_id'],
        telegram_login=data['telegram_login'],
        name=data['name'],
        phone=data['phone'],
        email=data['email'],
        index=data['index'],
        city=data['city'],
        address=data['address'],
        date_reg=data['date_reg'],
    )
    session.add(obj)
    await session.commit()


"""Выгрузка всех Telegram ID участников"""


async def get_users_all(session: AsyncSession):
    query = select(Telegram_ID.telegram_id)
    result = await session.execute(query)
    user_ids = [row[0] for row in result.fetchall()]
    return user_ids


"""Проверка на наличие Telegram ID"""


async def get_user_unique(session: AsyncSession, telegram_id: int):
    query = select(func.count(User.telegram_id)).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    user_count = result.scalars().all()
    print(f'user_count={user_count[0]}')
    if user_count[0] == 0:
        return False
    else:
        return True


"""Выгрузка информации про участника по Telegram ID"""


async def get_user_results(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(Result)
        .where(User.telegram_id == telegram_id)
        .join(User, Result.user_id == User.id)
    )

    distances = result.scalars().all()  # Получаем все результаты

    # Инициализируем значения для distance_1, distance_2 и distance_3
    distance_1 = 0
    distance_2 = 0
    distance_3 = 0

    # Суммируем значения для каждого distance
    for entry in distances:
        distance_1 += entry.distance_1
        distance_2 += entry.distance_2
        distance_3 += entry.distance_3

    return distance_1, distance_2, distance_3


"""Подсчет результата всех дней"""


async def get_total_distance(session: AsyncSession, telegram_id: int) -> float:
    # Выполняем запрос для получения суммы
    result = await session.execute(
        select(
            func.coalesce(func.sum(Result.distance_1), 0) +
            func.coalesce(func.sum(Result.distance_2), 0)
        ).join(User).filter(User.telegram_id == telegram_id)
    )

    total_distance = result.scalar_one_or_none()
    return total_distance or 0.0


"""Выгрузка информации про участника по login"""


async def get_user_login(session: AsyncSession, telegram_login):
    query = select(User).where(User.telegram_login == telegram_login)
    result = await session.execute(query)
    user = result.scalars().first()
    return user


"""Выгрузка информации про участника по id записи"""


async def get_user_id(session: AsyncSession, id_user):
    query = select(User).where(User.id == id_user)
    result = await session.execute(query)
    user = result.scalars().first()
    return user


async def get_user_for_change(session: AsyncSession, telegram_id: int):
    query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    return result.scalar()


"""Изменение данных участника"""


async def update_user(session: AsyncSession, telegram_id: int, data):
    query = update(User).where(User.id == telegram_id).values(
        telegram_id=data['telegram_id'],
        name=data['name'],
        phone=data['phone'],
        email=data['email'],
        index=data['index'],
        city=data['city'],
        address=data['address'],
        date_reg=data['date_reg'],
    )
    await session.execute(query)
    await session.commit()


"""Изменение результатов участника за 1ый день"""


async def add_result_for_user(session: AsyncSession, telegram_id: int, data):
    # Найти пользователя по telegram_id
    user_query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(user_query)
    user = result.scalars().first()

    if user is None:
        raise ValueError(f"User  with telegram_id {telegram_id} not found.")

    # Создать новую запись в таблице Result
    new_result = Result(
        user_id=user.id,  # Устанавливаем связь с пользователем
        distance_1=data.get('distance_1'),
        photo_1=data.get('photo_1'),
        story_1=data.get('story_1'),
        date_1=data.get('date_1')
    )

    session.add(new_result)
    await session.commit()


"""Изменение результатов участника за 2ый день"""


async def update_result2_for_user(session: AsyncSession, telegram_id: int, data):
    user_query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(user_query)
    user = result.scalars().first()

    if user is None:
        raise ValueError(f"User  with telegram_id {telegram_id} not found.")

    result_query = select(Result).where(Result.user_id == user.id)
    result_record = await session.execute(result_query)
    existing_result = result_record.scalars().first()

    if existing_result is None:
        raise ValueError(f"No result found for user with telegram_id {telegram_id}.")

    # Обновить поля записи
    existing_result.distance_2 = data.get('distance_2', existing_result.distance_2)
    existing_result.photo_2 = data.get('photo_2', existing_result.photo_2)
    existing_result.story_2 = data.get('story_2', existing_result.story_2)
    existing_result.date_2 = data.get('date_2', existing_result.date_2)

    # Сохранить изменения
    await session.commit()

    return existing_result  # Возвращаем обновленную запись


"""Изменение результатов участника за 3ый день"""


async def update_result3_for_user(session: AsyncSession, telegram_id: int, data):
    user_query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(user_query)
    user = result.scalars().first()

    if user is None:
        raise ValueError(f"User  with telegram_id {telegram_id} not found.")

    result_query = select(Result).where(Result.user_id == user.id)
    result_record = await session.execute(result_query)
    existing_result = result_record.scalars().first()

    if existing_result is None:
        raise ValueError(f"No result found for user with telegram_id {telegram_id}.")

    # Обновить поля записи
    existing_result.distance_3 = data.get('distance_3', existing_result.distance_3)
    existing_result.photo_3 = data.get('photo_3', existing_result.photo_3)
    existing_result.story_3 = data.get('story_3', existing_result.story_3)
    existing_result.date_3 = data.get('date_3', existing_result.date_3)
    existing_result.result = data.get('result', existing_result.result)

    # Сохранить изменения
    await session.commit()

    return existing_result  # Возвращаем обновленную запись


"""Удаление данных участника"""


async def delete_user(session: AsyncSession, telegram_id: int):
    query = delete(User).where(User.id == telegram_id)
    await session.execute(query)
    await session.commit()
