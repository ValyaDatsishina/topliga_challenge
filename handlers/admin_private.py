import asyncio
import logging
from datetime import datetime

from aiogram import F, Router, types, Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from handlers.chat_types import ChatTypeFilter, IsAdmin
from database.orm_query import get_user_results, get_user_login, get_user_id, get_users_all, \
    get_users_with_distance_1_2_no_distance_3, get_users_with_distance_1_no_distance_2, get_users_not_in_result, \
    get_users_not_in_user, get_users_with_all_distances
from handlers.keyboards import get_keyboard

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_KB = get_keyboard(
    "Проверить фото по ID пользователя",
    "Проверить фото по username",
    "Проверить фото по ID записи",
    "Отправить сообщение всем участникам",
    "Включить напоминания участникам",
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


# Функция для отправки сообщения всем пользователям
# Функция для отправки сообщения всем пользователям
async def send_message_to_all_users(session: AsyncSession, bot: Bot):
    # Определяем текст сообщения в зависимости от дня недели
    day_of_week = datetime.now().strftime('%A')  # Получаем текущий день недели

    message_text = (f"day_of_week = {day_of_week}")
    if day_of_week == "Thursday":
        message_text = ("Привет от Марафонского бота! На этих выходных начинается заключительный челлендж посвященный"
                        " RAY SIRIUS AUTODROM ⚡️Это твой последний шанс принять участие в розыгрыше от "
                        "титульного партнера марафона, спортивного бренда RAY.\n"
                        "\nНапоминаем, что каждый участник челленджа получит:\n"
                        "- место в рейтинге по завершении Челленджа;\n"
                        "- увеличенную скидку на регистрацию на 2 использования; \n"
                        "- возможность получить уникальную нашивку за участие в двух и более этапах.\n")
        user_ids = await get_users_all(session)
    elif day_of_week == "Friday":
        message_text = (
            "Привет-привет! Уже вечер, а ты до сих пор не загрузил трек тренировки! Выходи на пробежку прямо сейчас "
            "и жми на команду /day_1 💫")
        user_ids = await get_users_not_in_result(session)
    elif day_of_week == "Saturday":
        message_text = "Это снова я 👋🏻 Напоминаю про пробежку второго дня, загрузи ее по команде /day_2 "
        user_ids = await get_users_with_distance_1_no_distance_2(session)

    elif day_of_week == "Sunday":
        message_text = ("Привет! Осталось совсем чуть-чуть, загрузи последний трек /day_3 "
                        "и ты получишь промокод на скидку 15% для себя и друзей 🎁")
        user_ids = await get_users_with_distance_1_2_no_distance_3(session)
    elif day_of_week == "Monday":
        message_text = ("Привет! Промокод на скидку скоро сгорит, успей зарегаться и позвать друга /promo.")
        user_ids = await get_users_with_all_distances(session)
    else:
        message_text = "Легких будней!"
        user_ids = await get_users_all(session)
    # user_ids = await get_users_all(session)
    for user_id in user_ids:
        try:
            # Отправляем сообщение каждому пользователю
            await bot.send_message(user_id, message_text)
            await asyncio.sleep(3)
        except TelegramForbiddenError as e:
            # Удалите пользователя из списка
            user_ids.remove(user_id)
            # Обработайте ошибку
            logging.error(f"Ошибка: {e} - Бот был заблокирован пользователем")


scheduler = AsyncIOScheduler()


def schedule_message(session: AsyncSession, bot: Bot):
    # Укажите дни недели (0=понедельник, 6=воскресенье) и время (часы и минуты)
    job = scheduler.add_job(
        send_message_to_all_users,
        CronTrigger(day_of_week='thu,fri,sat,sun,mon', hour=16, minute=10),
        args=[session, bot]  # Передаем только сессию и бот
    )
    # Запускаем планировщик, если он еще не запущен
    if not scheduler.running:
        scheduler.start()

    return job.id  # Возвращаем идентификатор задачи


async def stop_message_schedule(job_id: str):
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
        logging.info("Рассылка сообщений остановлена.")
    else:
        logging.warning("Задача не найдена.")


@admin_router.message(StateFilter(None), F.text == "Остановить рассылку сообщений")
async def stop_sent_message(message: types.Message, state: FSMContext):
    job_data = await state.get_data()  # Получаем данные состояния
    job_id = job_data.get('job_id')  # Извлекаем идентификатор задачи
    if job_id:
        await stop_message_schedule(job_id)
        await message.answer("Рассылка сообщений остановлена.")
    else:
        await message.answer("Рассылка сообщений не была запущена.")
    await state.clear()


"""Отложенные отправки сообщений всем участникам"""


@admin_router.message(StateFilter(None), F.text == "Включить напоминания участникам")
async def sent_message(message: types.Message, state: FSMContext, session: AsyncSession, bot: Bot):
    await message.answer(f"Сообщения отправляются")
    schedule_message(session, bot)
    await state.clear()


@admin_router.message(State('*'), or_f(Command("cancel"), F.text.lower() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


@admin_router.message(StateFilter(None), Command("admin"))
async def check_photo(message: types.Message, state: FSMContext):
    await message.answer(f"Выбрать способ поиска", reply_markup=ADMIN_KB)
    # await state.set_state(CheckPhoto_telegram_id.telegram_id)


@admin_router.message(StateFilter(None), F.text == "Проверить фото по ID пользователя")
async def check_photo(message: types.Message, state: FSMContext):
    await message.answer(f"Введите  ID  участника")
    await state.set_state(CheckPhoto_telegram_id.telegram_id)


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
    user_result = await get_user_results(session, telegram_id)
    if user_result:
        user, result = user_result

        await message.answer(f"Участник {user.name} "
                             f"\nЛогин @{user.telegram_login}"
                             f"\nОбщая дистанция {result.result}")
        if result.photo_1:
            await message.answer_photo(
                result.photo_1,
                caption=f"Дистанция первого дня: {result.distance_1}")
            await message.answer_photo(result.story_1)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал в первый день‼️")
        if result.photo_2:
            await message.answer_photo(
                result.photo_2,
                caption=f"Дистанция второго дня: {result.distance_2}")
            await message.answer_photo(result.story_2)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал во второй день‼️")
        if result.photo_3:
            await message.answer_photo(
                result.photo_3,
                caption=f"Дистанция третьего дня: {result.distance_3}")
            await message.answer_photo(result.story_3, reply_markup=ADMIN_KB)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал в третий день‼️", reply_markup=ADMIN_KB)
    await state.clear()


@admin_router.message(CheckPhoto_login.telegram_login)
async def get_photo(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_login = message.text
    user_result = await get_user_login(session, telegram_login)

    if user_result:
        user, result = user_result

        await message.answer(f"Участник {user.name} "
                             f"\nЛогин @{user.telegram_login}"
                             f"\nОбщая дистанция {result.result}")
        if result.photo_1:
            await message.answer_photo(
                result.photo_1,
                caption=f"Дистанция первого дня: {result.distance_1}")
            await message.answer_photo(result.story_1)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал в первый день‼️")
        if result.photo_2:
            await message.answer_photo(
                result.photo_2,
                caption=f"Дистанция второго дня: {result.distance_2}")
            await message.answer_photo(result.story_2)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал во второй день‼️")
        if result.photo_3:
            await message.answer_photo(
                result.photo_3,
                caption=f"Дистанция третьего дня: {result.distance_3}")
            await message.answer_photo(result.story_3, reply_markup=ADMIN_KB)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал в третий день‼️", reply_markup=ADMIN_KB)
    await state.clear()


@admin_router.message(CheckPhoto_id.id)
async def get_photo(message: types.Message, state: FSMContext, session: AsyncSession):
    result_id = int(message.text)
    # is_user_exist = await get_user_id_unique(session, id_user)
    # if is_user_exist:
    user_result = await get_user_id(session, result_id)
    if user_result:
        user, result = user_result
        await message.answer(f"Участник {user.name} "
                             f"\nЛогин @{user.telegram_login}"
                             f"\nОбщая дистанция {result.result}")
        if result.photo_1:
            await message.answer_photo(
                result.photo_1,
                caption=f"Дистанция первого дня: {result.distance_1}")
            await message.answer_photo(result.story_1)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал в первый день‼️")
        if result.photo_2:
            await message.answer_photo(
                result.photo_2,
                caption=f"Дистанция второго дня: {result.distance_2}")
            await message.answer_photo(result.story_2)
        else:
            await message.answer(f"‼️Участник {user.name} не пробежал во второй день‼️")
        if result.photo_3:
            await message.answer_photo(
                result.photo_3,
                caption=f"Дистанция третьего дня: {result.distance_3}")
            await message.answer_photo(result.story_3, reply_markup=ADMIN_KB)
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
