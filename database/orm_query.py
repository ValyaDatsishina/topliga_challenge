from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database.models import User, Result1, Telegram_ID, Promo

"""Добавление в бд нового участника"""


async def add_user(session: AsyncSession, data: dict):
    obj = User(
        telegram_id=data['telegram_id'],
        telegram_login=data['telegram_login'],
        name=data['name'],
        phone=data['phone'],
        email=data['email'],
        date_reg=data['date_reg'],
    )

    # Проверяем, существует ли telegram_id в таблице Telegram_ID
    result = await session.execute(select(Telegram_ID).filter_by(telegram_id=data['telegram_id']))
    existing_telegram_id = result.scalars().first()

    # Если telegram_id не существует, добавляем его
    if existing_telegram_id is None:
        telegram_id = Telegram_ID(telegram_id=data['telegram_id'])
        session.add(telegram_id)

    session.add(obj)
    await session.commit()


"""Выгрузка всех Telegram ID участников"""


async def get_users_all(session: AsyncSession):
    query = select(Telegram_ID.telegram_id)
    result = await session.execute(query)
    user_ids = [row[0] for row in result.fetchall()]
    return user_ids


"""Выгрузка  Telegram ID участников, которые не зарегистрировались"""


async def get_users_not_in_user(session: AsyncSession):
    query = select(Telegram_ID.telegram_id).where(
        Telegram_ID.telegram_id.notin_(
            select(User.telegram_id)
        )
    )

    result = await session.execute(query)
    user_ids = [row[0] for row in result.fetchall()]
    return user_ids


"""Выгрузка  Telegram ID участников, которые зарегистрировались, но не записали первый день """


async def get_users_not_in_result(session: AsyncSession):
    # Запрос для получения telegram_id из User, которых нет в Result
    query = select(User.telegram_id).where(
        User.id.notin_(
            select(Result1.user_id)
        )
    )

    result = await session.execute(query)
    telegram_ids = [row[0] for row in result.fetchall()]
    return telegram_ids


"""Выгрузка Telegram ID участников, у которых есть первый день и нет второго  """


async def get_users_with_distance_1_no_distance_2(session: AsyncSession):
    # Запрос для получения telegram_id из User, у которых есть distance_1 и нет distance_2 в Result
    query = select(User.telegram_id).where(
        User.id.in_(
            select(Result1.user_id).where(
                Result1.distance_1.isnot(None),  # distance_1 должно быть не None
                Result1.distance_2.is_(None)  # distance_2 должно быть None
            )
        )
    )

    result = await session.execute(query)
    telegram_ids = [row[0] for row in result.fetchall()]
    return telegram_ids


"""Выгрузка Telegram ID участников, у которых есть первый и второй день и нет третьего  """


async def get_users_with_distance_1_2_no_distance_3(session: AsyncSession):
    # Запрос для получения telegram_id из User, у которых есть distance_1 и нет distance_2 в Result
    query = select(User.telegram_id).where(
        User.id.in_(
            select(Result1.user_id).where(
                Result1.distance_1.isnot(None),
                Result1.distance_2.isnot(None),  # distance_1 должно быть не None
                Result1.distance_3.is_(None)  # distance_2 должно быть None
            )
        )
    )

    result = await session.execute(query)
    telegram_ids = [row[0] for row in result.fetchall()]
    return telegram_ids


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


"""Проверка на наличие записи в result"""


async def get_result_unique(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(func.count(Result1.user_id))
        .where(User.telegram_id == telegram_id)
        .join(User, Result1.user_id == User.id)
    )
    # result = await session.execute(query)
    user_count = result.scalars().all()
    print(f'user_count={user_count[0]}')
    if user_count[0] == 0:
        return False
    else:
        return True


"""Выгрузка дистанций по Telegram ID"""


async def get_user_distances(session: AsyncSession, telegram_id: int):
    result = await session.execute(
        select(Result1)
        .where(User.telegram_id == telegram_id)
        .join(User, Result1.user_id == User.id)
    )

    distances = result.scalars().all()  # Получаем все результаты

    distance_1 = 0
    distance_2 = 0
    distance_3 = 0

    for entry in distances:
        distance_1 += entry.distance_1
        distance_2 += entry.distance_2
        distance_3 += entry.distance_3

    return distance_1, distance_2, distance_3


"""Проверка, что участник бежал все дни"""


async def check_distances_filled(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(
        select(Result1)
        .where(User.telegram_id == telegram_id)
        .join(User, Result1.user_id == User.id)
    )
    user = result.scalars().first()

    if not user:
        return False

    results = user.result
    if not results:
        return False

    if user.distance_1 is None or user.distance_2 is None or user.distance_3 is None:
        return False

    return True


"""Подсчет результата всех дней"""


async def get_total_distance(session: AsyncSession, telegram_id: int) -> float:
    # Выполняем запрос для получения суммы
    result = await session.execute(
        select(
            func.coalesce(func.sum(Result1.distance_1), 0) +
            func.coalesce(func.sum(Result1.distance_2), 0)
        ).join(User).filter(User.telegram_id == telegram_id)
    )

    total_distance = result.scalar_one_or_none()
    return total_distance or 0.0


"""Выдача промо-кода"""


async def get_promo_code(session: AsyncSession, telegram_id: int) -> str:
    # Получаем результат по ID
    user_query = await session.execute(select(User).filter(User.telegram_id == telegram_id))
    user = user_query.scalars().first()

    if not user:
        return "User  not found"

    user_id = user.id  # Получаем user_id

    # Получаем результаты по user_id
    result_query = await session.execute(select(Result1).filter(Result1.user_id == user_id))
    result = result_query.scalars().first()

    if not result:
        return "Result not found"

    promo_query = await session.execute(select(Promo).filter(Promo.id == result.id))  # Замените условие, если нужно
    promo = promo_query.scalars().first()

    if not promo:
        return "Promo code not found"

    return promo.Code


"""Выгрузка информации про участника по Telegram ID"""


async def get_user_results(session: AsyncSession, telegram_id):
    result = await session.execute(
        select(User, Result1).join(Result1).filter(User.telegram_id == telegram_id)
    )

    results = result.first()
    # Получаем все результаты
    return results


"""Выгрузка информации про участника по login"""


async def get_user_login(session: AsyncSession, telegram_login):
    result = await session.execute(
        select(User, Result1).join(Result1).filter(User.telegram_login == telegram_login)
    )

    results = result.first()  # Получаем все результаты
    return results


"""Выгрузка информации про участника по id записи"""


async def get_user_id(session: AsyncSession, result_id):
    result = await session.execute(
        select(User, Result1).join(Result1).filter(Result1.id == result_id)
    )

    results = result.first()  # Получаем все результаты
    return results


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
        date_reg=data['date_reg'],
    )
    await session.execute(query)
    await session.commit()


"""Добавление записи результатов участника за 1ый день"""


async def add_result_for_user(session: AsyncSession, telegram_id: int, data):
    # Найти пользователя по telegram_id
    user_query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(user_query)
    user = result.scalars().first()

    if user is None:
        raise ValueError(f"User  with telegram_id {telegram_id} not found.")

    # Создать новую запись в таблице Result
    new_result = Result1(
        user_id=user.id,  # Устанавливаем связь с пользователем
        distance_1=data.get('distance_1'),
        photo_1=data.get('photo_1'),
        story_1=data.get('story_1'),
        date_1=data.get('date_1')
    )

    session.add(new_result)
    await session.commit()


"""Изменение результатов участника за 1ый день"""


async def update_result1_for_user(session: AsyncSession, telegram_id: int, data):
    user_query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(user_query)
    user = result.scalars().first()

    if user is None:
        raise ValueError(f"User  with telegram_id {telegram_id} not found.")

    result_query = select(Result1).where(Result1.user_id == user.id)
    result_record = await session.execute(result_query)
    existing_result = result_record.scalars().first()

    if existing_result is None:
        raise ValueError(f"No result found for user with telegram_id {telegram_id}.")

    # Обновить поля записи
    existing_result.distance_1 = data.get('distance_1', existing_result.distance_1)
    existing_result.photo_1 = data.get('photo_1', existing_result.photo_1)
    existing_result.story_1 = data.get('story_1', existing_result.story_1)
    existing_result.date_1 = data.get('date_1', existing_result.date_1)

    # Сохранить изменения
    await session.commit()

    return existing_result  # Возвращаем обновленную запись


"""Изменение результатов участника за 2ый день"""


async def update_result2_for_user(session: AsyncSession, telegram_id: int, data):
    user_query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(user_query)
    user = result.scalars().first()

    if user is None:
        raise ValueError(f"User  with telegram_id {telegram_id} not found.")

    result_query = select(Result1).where(Result1.user_id == user.id)
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

    result_query = select(Result1).where(Result1.user_id == user.id)
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
