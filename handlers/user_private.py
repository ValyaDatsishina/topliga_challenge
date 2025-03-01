import io
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from PIL import Image

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.chat_types import ChatTypeFilter
from database.orm_query import (
    add_user, add_result_for_user, update_result2_for_user, 
    update_result3_for_user, get_user_distances, get_user_unique, 
    get_total_distance, check_distances_filled, get_promo_code, 
    get_user_unique, get_user_results, update_result1_for_user
)
from handlers.frame_engine import add_frame
from handlers.keyboards import KeyboardFactory

# Инициализация роутера
user_router = Router()
user_router.message.filter(ChatTypeFilter(["private"]))

# Инициализация фабрики клавиатур
kb = KeyboardFactory()

# Константы для клавиатур
START_KB = kb.create_reply_keyboard(["Зарегистрироваться"])
DAY1_KB = kb.create_reply_keyboard(["Добавить результаты первого дня"])
DAY2_KB = kb.create_reply_keyboard(["Добавить результаты второго дня"])
DAY3_KB = kb.create_reply_keyboard(["Добавить результаты третьего дня"])
CHECK_KB = kb.create_reply_keyboard(["Показать мой результат", "Получить промокод"])
ALL_KB = kb.create_reply_keyboard(
    ["Зарегистрироваться", 
     "Добавить результаты первого дня",
     "Добавить результаты второго дня", 
     "Добавить результаты третьего дня"],
    sizes=(1, 1, 1, 1)
)

class BaseState(StatesGroup):
    """Базовый класс для состояний с общей функциональностью"""
    @classmethod
    async def validate_photo(cls, message: types.Message) -> bool:
        return bool(message.photo)
    
    @classmethod
    async def validate_distance(cls, text: str) -> bool:
        try:
            distance = float(text.replace(',', '.'))
            return 0 < distance < 100
        except ValueError:
            return False
    
    @classmethod
    async def process_photo(cls, photo: types.PhotoSize) -> bytes:
        """Обработка фотографии и сохранение в байтовый объект"""
        bio = io.BytesIO()
        file = await photo.bot.download(photo.file_id)
        bio.write(file.read())
        bio.seek(0)
        return bio.getvalue()

class AddUser(BaseState):
    name = State()
    phone = State()
    email = State()

    texts = {
        'name': 'Введите имя заново:',
        'phone': 'Введите номер телефона заново:',
        'email': 'Введите адрес электронной почты заново:',
    }
    
    @classmethod
    async def validate_phone(cls, text: str) -> bool:
        try:
            phone = int(text)
            return len(text) == 11 and text.startswith('7')
        except ValueError:
            return False

class ResultBase(BaseState):
    """Базовый класс для результатов дней"""
    distance = State()
    photo = State()
    frame = State()
    story = State()
    date = State()
    
    texts = {
        'photo': 'Загрузи фото заново:',
        'distance': 'Введи дистанцию в километрах',
        'frame': 'Загрузи фото заново:',
        'story': 'Загрузи фото заново:',
    }

class AddResult_1(ResultBase):
    pass

class AddResult_2(ResultBase):
    pass

class AddResult_3(ResultBase):
    result = State()

async def handle_result_day(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession,
    day: int,
    state_class: ResultBase,
    check_func: Callable,
    update_func: Callable
) -> None:
    """Общий обработчик для добавления результатов дня"""
    telegram_id = message.from_user.id
    if not await check_func(session, telegram_id):
        await message.answer(
            f"Сначала нужно добавить результаты предыдущего дня",
            reply_markup=ALL_KB
        )
        return
    
    await state.set_state(state_class.photo)
    await message.answer(f"Загрузи скриншот трека {day}-го дня")

# Общие обработчики для всех состояний
@user_router.message(State('*'), or_f(Command("cancel"), F.text.lower() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ALL_KB)

@user_router.message(StateFilter(None), or_f(Command("start"), F.text == "Участвовать в челлендже",
                                           F.text == "Зарегистрироваться"))
async def user_start(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    is_user_exist = await get_user_unique(session, telegram_id)
    
    if is_user_exist:
        user_result = await get_user_results(session, telegram_id)
        await message.answer(
            'Ты уже зарегистрирован!\n'
            'В меню доступны все команды. Важно добавлять тренировки по порядку.'
        )
        
        if user_result:
            user, result = user_result
            if not result.distance_1:
                await message.answer('Добавьте результаты первого дня челленджа.', reply_markup=DAY1_KB)
            elif not result.distance_2:
                await message.answer('Добавьте результаты второго дня челленджа.', reply_markup=DAY2_KB)
            elif not result.distance_3:
                await message.answer('Добавьте результаты третьего дня челленджа.', reply_markup=DAY3_KB)
            else:
                await message.answer(
                    f"{user.name}, поздравляем с окончанием челленджа ☀️\n"
                    f"День 1: {result.distance_1} км\n"
                    f"День 2: {result.distance_2} км\n"
                    f"День 3: {result.distance_3} км\n"
                    f"Общий результат: {result.result} км\n"
                    f"Отлично, так держать!"
                )
    else:
        await message.answer(
            'Привет от марафонского бота 👋\n'
            'Для участия нужно зарегистрироваться.\n'
            'Введите ваше имя:'
        )
        await state.set_state(AddUser.name)

# Обработчики регистрации
@user_router.message(AddUser.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if '/' in message.text or 'зарегистрироваться' in message.text.lower():
        await message.answer('Введите имя еще раз')
        return
    
    await state.update_data(
        name=message.text,
        telegram_id=message.from_user.id,
        telegram_login=message.from_user.username or 'неизвестный атлет'
    )
    await message.answer("Введите номер телефона в формате 7XXXXXXXXXX (без '+')")
    await state.set_state(AddUser.phone)

@user_router.message(AddUser.phone, F.text)
async def add_phone(message: types.Message, state: FSMContext):
    if not await AddUser.validate_phone(message.text):
        await message.answer("Введите корректный номер телефона в формате 7XXXXXXXXXX")
        return
    
    await state.update_data(phone=message.text)
    await message.answer("Введите email")
    await state.set_state(AddUser.email)

@user_router.message(AddUser.email, F.text)
async def add_email(message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    data.update({
        'email': message.text,
        'date_reg': datetime.now()
    })
    
    try:
        await add_user(session, data)
        await message.answer(
            "Регистрация успешна!\n"
            "Вперед на пробежку. Не забудьте записать трек тренировки и сделать стори 🔥",
            reply_markup=DAY1_KB
        )
    except Exception as e:
        logging.error(f"Error adding user: {e}")
        await message.answer(
            "Ошибка при регистрации. Убедитесь, что указано имя пользователя в профиле Telegram.",
            reply_markup=START_KB
        )
    
    await state.clear()

# Обработчики результатов
@user_router.message(StateFilter(None), or_f(Command("day_1"), F.text == "Добавить результаты первого дня"))
async def add_result_1(message: types.Message, state: FSMContext, session: AsyncSession):
    await handle_result_day(
        message, state, session,
        day=1,
        state_class=AddResult_1,
        check_func=get_user_unique,
        update_func=update_result1_for_user
    )

@user_router.message(StateFilter(None), or_f(Command("day_2"), F.text == "Добавить результаты второго дня"))
async def add_result_2(message: types.Message, state: FSMContext, session: AsyncSession):
    await handle_result_day(
        message, state, session,
        day=2,
        state_class=AddResult_2,
        check_func=get_user_unique,
        update_func=update_result2_for_user
    )

@user_router.message(StateFilter(None), or_f(Command("day_3"), F.text == "Добавить результаты третьего дня"))
async def add_result_3(message: types.Message, state: FSMContext, session: AsyncSession):
    await handle_result_day(
        message, state, session,
        day=3,
        state_class=AddResult_3,
        check_func=get_user_unique,
        update_func=update_result3_for_user
    )

# Обработчики фотографий для каждого дня
@user_router.message(AddResult_1.photo, F.photo)
async def handle_photo_day1(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фотографию")
        return
    
    photo_data = await BaseState.process_photo(message.photo[-1])
    await state.update_data(photo=photo_data)
    await state.set_state(AddResult_1.distance)
    await message.answer("Введите дистанцию в километрах")

@user_router.message(AddResult_2.photo, F.photo)
async def handle_photo_day2(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фотографию")
        return
    
    photo_data = await BaseState.process_photo(message.photo[-1])
    await state.update_data(photo=photo_data)
    await state.set_state(AddResult_2.distance)
    await message.answer("Введите дистанцию в километрах")

@user_router.message(AddResult_3.photo, F.photo)
async def handle_photo_day3(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фотографию")
        return
    
    photo_data = await BaseState.process_photo(message.photo[-1])
    await state.update_data(photo=photo_data)
    await state.set_state(AddResult_3.distance)
    await message.answer("Введите дистанцию в километрах")

# Обработчики дистанций для каждого дня
@user_router.message(AddResult_1.distance, F.text)
async def handle_distance_day1(message: types.Message, state: FSMContext, session: AsyncSession):
    if not await BaseState.validate_distance(message.text):
        await message.answer("Введите корректное значение дистанции (0-100 км)")
        return
    
    distance = float(message.text.replace(',', '.'))
    data = await state.get_data()
    data['distance'] = distance
    data['date'] = datetime.now()
    telegram_id = message.from_user.id
    
    try:
        await update_result1_for_user(
            session=session,
            telegram_id=telegram_id,
            data=data
        )
        await message.answer("Результат сохранен!", reply_markup=ALL_KB)
    except Exception as e:
        logging.error(f"Error updating result: {e}")
        await message.answer("Произошла ошибка при сохранении результата")
    
    await state.clear()

@user_router.message(AddResult_2.distance, F.text)
async def handle_distance_day2(message: types.Message, state: FSMContext, session: AsyncSession):
    if not await BaseState.validate_distance(message.text):
        await message.answer("Введите корректное значение дистанции (0-100 км)")
        return
    
    distance = float(message.text.replace(',', '.'))
    data = await state.get_data()
    data['distance'] = distance
    data['date'] = datetime.now()
    telegram_id = message.from_user.id
    
    try:
        await update_result2_for_user(
            session=session,
            telegram_id=telegram_id,
            data=data
        )
        await message.answer("Результат сохранен!", reply_markup=ALL_KB)
    except Exception as e:
        logging.error(f"Error updating result: {e}")
        await message.answer("Произошла ошибка при сохранении результата")
    
    await state.clear()

@user_router.message(AddResult_3.distance, F.text)
async def handle_distance_day3(message: types.Message, state: FSMContext, session: AsyncSession):
    if not await BaseState.validate_distance(message.text):
        await message.answer("Введите корректное значение дистанции (0-100 км)")
        return
    
    distance = float(message.text.replace(',', '.'))
    data = await state.get_data()
    data['distance'] = distance
    data['date'] = datetime.now()
    telegram_id = message.from_user.id
    
    try:
        await update_result3_for_user(
            session=session,
            telegram_id=telegram_id,
            data=data
        )
        await message.answer("Результат сохранен!", reply_markup=ALL_KB)
    except Exception as e:
        logging.error(f"Error updating result: {e}")
        await message.answer("Произошла ошибка при сохранении результата")
    
    await state.clear()

# Обработчики результатов и промокодов
@user_router.message(StateFilter(None), or_f(Command("result"), F.text == "Показать мой результат"))
async def get_result(message: types.Message, session: AsyncSession):
    telegram_id = message.from_user.id
    user_result = await get_user_results(session, telegram_id)
    
    if not user_result:
        await message.answer("Результаты не найдены", reply_markup=ALL_KB)
        return
    
    user, result = user_result
    if not all([result.distance_1, result.distance_2, result.distance_3]):
        await message.answer("Сначала завершите все три дня челленджа", reply_markup=ALL_KB)
        return
    
    await message.answer(
        f"{user.name}, ваши результаты:\n"
        f"День 1: {result.distance_1} км\n"
        f"День 2: {result.distance_2} км\n"
        f"День 3: {result.distance_3} км\n"
        f"Общий результат: {result.result} км"
    )

@user_router.message(StateFilter(None), or_f(Command("promo"), F.text == "Получить промокод"))
async def check_result(message: types.Message, session: AsyncSession):
    telegram_id = message.from_user.id
    if not await check_distances_filled(session, telegram_id):
        await message.answer(
            "Для получения промокода необходимо завершить все три дня челленджа",
            reply_markup=ALL_KB
        )
        return
    
    promo = await get_promo_code(session, telegram_id)
    if promo:
        await message.answer(
            f"Ваш промокод: {promo}\n"
            "Используйте его при регистрации на забег"
        )
    else:
        await message.answer("Промокод не найден", reply_markup=ALL_KB)
