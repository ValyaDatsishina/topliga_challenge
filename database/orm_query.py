from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from database.models import User, Telegram_ID

"""Добавление в бд нового участника"""


async def add_user(session: AsyncSession, data: dict):
    obj = User(
        telegram_id=data['telegram_id'],
        telegram_login=data['telegram_login'],
        name=data['name'],
        phone=data['phone'],
        email=data['email'],
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


async def get_user(session: AsyncSession, telegram_id: int):
    query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    user = result.scalars().first()
    return user


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
        email=data['email'], )
    await session.execute(query)
    await session.commit()


"""Изменение результатов участника за 1ый день"""


async def update_user_1(session: AsyncSession, telegram_id: int, data):
    query = update(User).where(User.telegram_id == telegram_id).values(
        distance_1=data['distance_1'],
        photo_1=data['photo_1'],
        story_1=data['story_1'],
        date_1=data['date_1'],
    )

    await session.execute(query)
    await session.commit()


"""Изменение результатов участника за 2ый день"""


async def update_user_2(session: AsyncSession, telegram_id: int, data):
    query = update(User).where(User.telegram_id == telegram_id).values(
        distance_2=data['distance_2'],
        photo_2=data['photo_2'],
        story_2=data['story_2'],
        date_2=data['date_2'],
    )
    await session.execute(query)
    await session.commit()


"""Изменение результатов участника за 3ый день"""


async def update_user_3(session: AsyncSession, telegram_id: int, data):
    query = update(User).where(User.telegram_id == telegram_id).values(
        distance_3=data['distance_3'],
        photo_3=data['photo_3'],
        date_3=data['date_3'],
        story_3=data['story_3'],
        index=data['index'],
        city=data['city'],
        address=data['address'],
        result=data['result'],
    )
    await session.execute(query)
    await session.commit()


"""Удаление данных участника"""


async def delete_user(session: AsyncSession, telegram_id: int):
    query = delete(User).where(User.id == telegram_id)
    await session.execute(query)
    await session.commit()
