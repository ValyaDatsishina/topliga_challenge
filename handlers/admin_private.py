import asyncio
import logging

from aiogram import F, Router, types, Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.chat_types import ChatTypeFilter, IsAdmin
from database.orm_query import get_user_results, get_user_login, get_user_id, get_users_all
from handlers.keyboards import get_keyboard


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_KB = get_keyboard(
    "Проверить фото по ID пользователя",
    "Проверить фото по username",
    "Проверить фото по ID записи",
    "Отправить сообщение всем участникам",
    placeholder="Выберите действие",
    sizes=(1, 1, 1, 1, 1)
)


"""Шаги состояний (FSM)"""

class CheckPhoto_telegram_id(StatesGroup):
    # Шаги состояний
    telegram_id = State()

    texts = {
        'AddProduct:telegram_id': 'Введите ID заново:'}


class CheckPhoto_login(StatesGroup):
    # Шаги состояний
    telegram_login = State()

    texts = {
        'AddProduct:telegram_login': 'Введите username заново:'}


class CheckPhoto_id(StatesGroup):
    # Шаги состояний
    id = State()

    texts = {
        'AddProduct:id': 'Введите id заново:'}


class MyForm(StatesGroup):
    message = State()


@admin_router.message(State('*'), or_f(Command("cancel"), F.text.lower() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


@admin_router.message(StateFilter(None), or_f(Command("admin"), F.text == "Проверить фото по ID пользователя"))
async def check_photo(message: types.Message, state: FSMContext):
    await message.answer(f"Выбрать способ поиска", reply_markup=ADMIN_KB)
    # await state.set_state(CheckPhoto_telegram_id.telegram_id)


@admin_router.message(StateFilter(None), F.text == "Проверить фото по ID пользователя")
async def check_photo(message: types.Message, state: FSMContext):
    await message.answer(f"Введите  ID  участника")
    await state.set_state(CheckPhoto_login.telegram_login)


@admin_router.message(StateFilter(None), F.text == "Проверить фото по ID записи")
async def check_photo(message: types.Message, state: FSMContext):
    await message.answer(f"Введите  ID  записи")
    await state.set_state(CheckPhoto_id.id)


@admin_router.message(StateFilter(None), F.text == "Проверить фото по username")
async def check_photo(message: types.Message, state: FSMContext):
    await message.answer(f"Введите username участника")
    await state.set_state(CheckPhoto_login.telegram_login)


@admin_router.message(CheckPhoto_telegram_id.telegram_id)
async def get_photo(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = int(message.text)
    user = await get_user_results(session, telegram_id)
    await message.answer(f"Участник {user.name} "
                         f"\nЛогин @{user.telegram_login}"
                         f"\nОбщая дистанция {user.result}")
    if user.photo_1:
        await message.answer_photo(
            user.photo_1,
            caption=f"Дистанция первого дня: {user.distance_1}")
        await message.answer_photo(user.story_1)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал в первый день‼️")
    if user.photo_2:
        await message.answer_photo(
            user.photo_2,
            caption=f"Дистанция второго дня: {user.distance_2}")
        await message.answer_photo(user.story_2)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал во второй день‼️")
    if user.photo_3:
        await message.answer_photo(
            user.photo_3,
            caption=f"Дистанция третьего дня: {user.distance_3}")
        await message.answer_photo(user.story_3, reply_markup=ADMIN_KB)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал в третий день‼️", reply_markup=ADMIN_KB)
    await state.clear()


@admin_router.message(CheckPhoto_login.telegram_login)
async def get_photo(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_login = message.text
    user = await get_user_login(session, telegram_login)
    await message.answer(f"Участник {user.name} "
                         f"\nЛогин @{user.telegram_login}"
                         f"\nОбщая дистанция {user.result}")
    if user.photo_1:
        await message.answer_photo(
            user.photo_1,
            caption=f"Дистанция первого дня: {user.distance_1}")
        await message.answer_photo(user.story_1)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал в первый день‼️")
    if user.photo_2:
        await message.answer_photo(
            user.photo_2,
            caption=f"Дистанция второго дня: {user.distance_2}")
        await message.answer_photo(user.story_2)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал во второй день‼️")
    if user.photo_3:
        await message.answer_photo(
            user.photo_3,
            caption=f"Дистанция третьего дня: {user.distance_3}")
        await message.answer_photo(user.story_3, reply_markup=ADMIN_KB)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал в третий день‼️", reply_markup=ADMIN_KB)
    await state.clear()


@admin_router.message(CheckPhoto_id.id)
async def get_photo(message: types.Message, state: FSMContext, session: AsyncSession):
    id_user = int(message.text)
    # is_user_exist = await get_user_id_unique(session, id_user)
    # if is_user_exist:
    user = await get_user_id(session, id_user)
    await message.answer(f"Участник {user.name} "
                         f"\nЛогин @{user.telegram_login}"
                         f"\nОбщая дистанция {user.result}")
    if user.photo_1:
        await message.answer_photo(
            user.photo_1,
            caption=f"Дистанция первого дня: {user.distance_1}")
        await message.answer_photo(user.story_1)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал в первый день‼️")
    if user.photo_2:
        await message.answer_photo(
            user.photo_2,
            caption=f"Дистанция второго дня: {user.distance_2}")
        await message.answer_photo(user.story_2)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал во второй день‼️")
    if user.photo_3:
        await message.answer_photo(
            user.photo_3,
            caption=f"Дистанция третьего дня: {user.distance_3}")
        await message.answer_photo(user.story_3, reply_markup=ADMIN_KB)
    else:
        await message.answer(f"‼️Участник {user.name} не пробежал в третий день‼️", reply_markup=ADMIN_KB)
    await state.clear()
    # else:
    #     await message.answer(f"️Eще нет такой записи", reply_markup=ADMIN_KB)


"""Код для отправки сообщения всем участникам"""

@admin_router.message(StateFilter(None), F.text == "Отправить сообщение всем участникам")
async def sent_message(message: types.Message, state: FSMContext):
    await message.answer(f"Введите текст для отправки письма всем пользователям")
    await state.set_state(MyForm.message)


@admin_router.message(MyForm.message)
async def handle_message_for_broadcast(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    await state.set_state()
    user_ids = await get_users_all(session)
    for user_id in user_ids:
        print(user_id)
        try:
            # Отправляем сообщение каждому пользователю
            await bot.send_message(user_id, message.text)
            await asyncio.sleep(3)
        except TelegramForbiddenError as e:
            # Удалите пользователя из списка
            user_ids.remove(user_id)
            print(f"Пользователь {user_id} был заблокирован, пропускаем его")
            # Обработайте ошибку
            print(f"Ошибка: {e} - Бот был заблокирован пользователем")
            logging.error(f"Ошибка: {e} - Бот был заблокирован пользователем")
