import io
import logging
import os
import tempfile
from datetime import datetime
from io import BytesIO
from PIL import Image

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputFile, FSInputFile

from sqlalchemy.ext.asyncio import AsyncSession

from handlers.chat_types import ChatTypeFilter
from database.orm_query import (add_user, add_result_for_user, update_result2_for_user, update_result3_for_user, \
                                get_user_distances, get_user_unique, get_total_distance, check_distances_filled,
                                get_promo_code, get_result_unique, get_user_results, update_result1_for_user)
from handlers.frame_engine import add_frame
from handlers.keyboards import get_keyboard

user_router = Router()
user_router.message.filter(ChatTypeFilter(["private"]))

START_KB = get_keyboard("Зарегистрироваться",
                        placeholder="Выберите действие",
                        )

DAY1_KB = get_keyboard("Добавить результаты первого дня",
                       placeholder="Выберите действие",
                       )

DAY2_KB = get_keyboard("Добавить результаты второго дня",
                       placeholder="Выберите действие",
                       )

DAY3_KB = get_keyboard("Добавить результаты третьего дня",
                       placeholder="Выберите действие",
                       )

CHECK_KB = get_keyboard("Показать мой результат",
                        "Получить промокод",
                        placeholder="Выберите действие", )

ALL_KB = get_keyboard("Зарегистрироваться",
                      "Добавить результаты первого дня",
                      "Добавить результаты второго дня",
                      "Добавить результаты третьего дня",
                      placeholder="Выберите действие",
                      sizes=(1, 1, 1, 1)
                      )

"""Шаги состояний (FSM)"""


class AddUser(StatesGroup):
    name = State()
    phone = State()
    email = State()

    texts = {
        'AddUser:name': 'Введите имя заново:',
        'AddUser:phone': 'Введите номер телефона заново:',
        'AddUser:email': 'Введите адрес электронной почты заново:', }


class AddResult_1(StatesGroup):
    distance_1 = State()
    photo_1 = State()
    frame_1 = State()
    story_1 = State()
    date_1 = State()

    texts = {
        'AddResult_1:photo_1': 'Загрузи фото заново:',
        'AddResult_1:distance_1': 'Введи дистанцию в километрах',
        'AddResult_1:frame_1': 'Загрузи фото заново:',
        'AddResult_1:story_1': 'Загрузи фото заново:', }


class AddResult_2(StatesGroup):
    distance_2 = State()
    photo_2 = State()
    frame_2 = State()
    story_2 = State()
    date_2 = State()

    texts = {
        'AddResult_2:photo_2': 'Загрузи фото заново:',
        'AddResult_2:distance_2': 'Введи дистанцию в километрах',
        'AddResult_2:frame_2': 'Загрузи фото заново:',
        'AddResult_2:story_2': 'Загрузи фото заново:', }


class AddResult_3(StatesGroup):
    distance_3 = State()
    photo_3 = State()
    frame_3 = State()
    story_3 = State()
    date_3 = State()
    result = State()

    field_for_change = None

    texts = {
        'AddResult_3:photo_3': 'Загрузи фото заново:',
        'AddResult_3:distance_3': 'Введи дистанцию в километрах',
        'AddResult_3:frame_3': 'Загрузи фото заново:',
        'AddResult_3:story_3': 'Загрузи фото заново:',
        'AddResult_3:index': 'Введи индекс заново:',
        'AddResult_3:city': 'Введи город заново:',
        'AddResult_3:address': 'Введи адрес заново:',
    }


"""Начало кода"""


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
        await message.answer(f'Ты уже зарегистрирован! \n'
                             f'\nВ меню, рядом со строчкой ввода текста, видны все доступные команды. '
                             f'Очень важно добавлять записи тренировок по порядку, '
                             f'чтобы итоговый результат посчитался верно.')
        if user_result:
            user, result = user_result
            if not result.distance_1:
                await message.answer(f'Но вы не добавили результаты первого дня челленджа.', reply_markup=DAY1_KB)
            elif not result.distance_2:
                await message.answer(f'Но вы не добавили результаты второго дня челленджа.', reply_markup=DAY2_KB)
            elif not result.distance_3:
                await message.answer(f'Но вы не добавили результаты третьего дня челленджа.', reply_markup=DAY3_KB)
            else:
                await message.answer(f"{user.name}, поздравляем вас с окончанием челленджа ☀️"
                                     f"\nВ первый день вы преодолели {result.distance_1} км"
                                     f"\nВо второй день: {result.distance_2} км"
                                     f"\nВ третий день: {result.distance_3} км"
                                     f"\nОбщий результат: {result.result} км"
                                     f"\nОтлично, так держать!")

    else:
        await message.answer(f'Привет от марафонского бота 👋 Начинаем подготовку к жаркому открытию сезона, '
                             f'к RAY SIRIUS AUTODROM ⚡️\n'
                             f'\nУсловия челленджа:'
                             f'\n1. Выходить на пробежку три дня подряд с 14 по 16 февраля;'
                             f'\n2. Присылать трек пробежки в тот же день в чат-бот;'
                             f'\n3. Выкладывать стори о пробежках в любых соц сетях - картинку с вашем '
                             f'фото пришлет чат-бот!\n'
                             f'\nКаждый участник челленджа получит:\n'
                             f'- место в рейтинге по завершению Челленджа;\n'
                             f'- увеличенную скидку на регистрацию на 2 использования; \n'
                             f'- возможность получить уникальную нашивку;\n'
                             f'- возможность выиграть призы от титульного партнера марафона, спортивного бренда RAY.'
                             , parse_mode='Markdown')
        await message.answer(
            f'Если ты допустил ошибку при вводе данных, нажми /cancel и начни сначала.\n'
            f'\nВ меню, рядом со строчкой ввода текста, видны все доступные команды. '
            f'Очень важно добавлять записи тренировок по порядку, чтобы итоговый результат посчитался верно.')
        await message.answer(f'Для участия нужно зарегистрироваться. \nВведи Имя')
        await state.set_state(AddUser.name)


@user_router.message(AddUser.name, or_f(F.text, F.text == "."))
async def add_name(message: types.Message, state: FSMContext):
    if '/' in message.text or 'зарегистрироваться' in message.text.lower():
        await message.answer(f'Введи Имя еще раз')
        return
    else:
        await state.update_data(name=message.text)
        user = message.from_user
        await state.update_data(telegram_id=user.id)
        await state.update_data(telegram_login=user.username)
        # else:
        #     await state.update_data(telegram_login='неизвестный атлет')
        await message.answer("Введи номер телефона в формате 7хххххххххх (без '+')")
        await state.set_state(AddUser.phone)


@user_router.message(AddUser.name)
async def name_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, введи Имя заново")


@user_router.message(AddUser.phone, or_f(F.text, F.text == "."))
async def add_phone(message: types.Message, state: FSMContext):
    try:
        int(message.text)
        if len(message.text) != 11:
            raise Exception('incorrect phone number length')
    except ValueError:
        await message.answer("Введи номер телефона без дополнительных символов")

        return
    except Exception:
        await message.answer("Некорректная длина номер телефона, введи номер телефона еще раз")
        return
    await state.update_data(phone=message.text)

    await message.answer("Введи email")
    await state.set_state(AddUser.email)


@user_router.message(AddUser.phone)
async def phone_validation(message: types.Message, state: FSMContext):
    await message.answer("Введены недопустимые данные, введи номер телефона заново")


@user_router.message(AddUser.email, or_f(F.text, F.text == "."))
async def add_email(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(email=message.text)
    await state.update_data(date_reg=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    print(f'telegram_id = {telegram_id}, data = {data}')
    try:
        await add_user(session, data)
        await message.answer("Отлично, ты зарегистирован!\n"
                             "Вперед на пробежку. Не забудь записать трек тренировки и сделать стори 🔥",
                             reply_markup=DAY1_KB, parse_mode='Markdown')

        await message.answer("Нажми команду /day_1 или кнопку, чтобы добавить первую пробежку", reply_markup=DAY1_KB)

    except Exception as e:
        await message.answer(
            f"Данные не сохранены. Проверь, что в ваш телеграм аккаунт введено имя пользователя, "
            f"по нему потом будет составляться турнирная таблица."
            f"\nДобавьте имя пользователя в профиле и попробуйте снова.",
            reply_markup=START_KB,
        )
        await state.clear()

    await state.clear()


# @user_router.message(AddUser.email)
# async def email_validation(message: types.Message, state: FSMContext):
#     await message.answer("Введены недопустимые данные, введи почту заново")
#
#
# @user_router.message(AddUser.index, or_f(F.text, F.text == "."))
# async def add_index(message: types.Message, state: FSMContext):
#     try:
#         int(message.text)
#     except ValueError:
#         await message.answer("Введите индекс без дополнительных символов и пробелов")
#         return
#     await state.update_data(index=message.text)
#     await message.answer("Напишите ваш город")
#     await state.set_state(AddUser.city)
#
#
# @user_router.message(AddUser.index)
# async def index_validation(message: types.Message):
#     await message.answer("Вы ввелине допустимые данные, введите индекс заново")
#
#
# @user_router.message(AddUser.city, or_f(F.text, F.text == "."))
# async def add_city(message: types.Message, state: FSMContext):
#     await state.update_data(city=message.text)
#     await message.answer("Напишите ваш адрес, и не забудьте указать номер квартиру. "
#                          "Иначе подарок вас не найдет 😊")
#     await state.set_state(AddUser.address)


# @user_router.message(AddUser.city)
# async def city_validation(message: types.Message):
#     await message.answer("Введены недопустимые данные, введи город заново")


# @user_router.message(AddUser.address, or_f(F.text, F.text == "."))
# async def add_address(message: types.Message, state: FSMContext, session: AsyncSession):
#     await state.update_data(address=message.text)
#     await state.update_data(date_reg=datetime.now())
#     telegram_id = int(message.from_user.id)
#     data = await state.get_data()
#     print(f'telegram_id = {telegram_id}, data = {data}')
#     try:
#         await add_user(session, data)
#         await message.answer("Отлично, вы зарегистированы!"
#                              "\nВперед на пробежку! "
#                              "Не забудьте записать трек тренировки, а также сделать сториз.",
#                              reply_markup=DAY1_KB, parse_mode='Markdown')
#
#         await message.answer("Нажмите команду /day_1 или кнопку, чтобы добавить первую пробежку", reply_markup=DAY1_KB)
#
#     except Exception as e:
#         await message.answer(
#             f"Данные не сохранены. Проверьте, что в ваш телеграм аккаунт введено имя пользователя, "
#             f"по нему потом будет составляться турнирная таблица."
#             f"\nДобавьте имя пользователя в профиле и попробуйте снова.",
#             reply_markup=START_KB,
#         )
#         await state.clear()
#
#     await state.clear()


"""Запись первого дня челленджа"""


@user_router.message(StateFilter(None), or_f(Command("day_1"), F.text == "Добавить результаты первого дня"))
async def add_result_1(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        await message.answer(f"Отправь скриншот пробежки любого бегового приложения или трекера, "
                             f"где видно дистанцию первого дня (загрузи только одно изображение)")
        await state.set_state(AddResult_1.photo_1)
    else:
        await message.answer("Ты еще не зарегистрировался. "
                             "\nПопробуй начать сначала",
                             reply_markup=START_KB)


@user_router.message(AddResult_1.photo_1, or_f(F.photo, F.text == "."))
async def add_photo_1(message: types.Message, state: FSMContext):
    await state.update_data(photo_1=message.photo[-1].file_id)
    await message.answer("Какую дистанцию ты пробежал в километрах?"
                         "\nУкажи только число через точку(например 21.1)")
    await state.set_state(AddResult_1.distance_1)


@user_router.message(AddResult_1.photo_1)
async def photo_1_validation(message: types.Message):
    await message.answer("Отправь скриншот забега, только одно изображение.")


@user_router.message(AddResult_1.distance_1, or_f(F.text, F.text == "."))
async def add_distance_1(message: types.Message, state: FSMContext):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Пиши дистанцию через точку в километрах. "
                             "Другие символы не используйте, пожалуйста."
                             "\n(Например 21.1)")
        return
    await state.update_data(distance_1=float(message.text))
    await message.answer("Отправь фото с пробежки и мы пришлем его в обработке в стилистике мероприятия."
                         "\nВыложи картинку в стори в любых соц сетях или мессенджерах.")
    await state.set_state(AddResult_1.frame_1)


@user_router.message(AddResult_1.distance_1)
async def distance_1_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, введи дистанцию заново")


@user_router.message(AddResult_1.frame_1, or_f(F.photo))
async def add_frame_1(message: types.Message, state: FSMContext):
    try:
        photo = message.photo[-1]  # Получаем наибольшую версию фото
        file_id = photo.file_id  # Получаем file_id для загрузки

        # Получаем файл с помощью bot.get_file()
        file = await message.bot.get_file(file_id)

        # Скачиваем файл
        photo_file = await message.bot.download_file(file.file_path)
        await message.answer("Пожалуйста, подожди, я добавляю рамку 🪄")

        # Открываем изображение с помощью Pillow
        image = Image.open(photo_file).convert("RGBA")

        output_file_path = add_frame(image, 1)

        if not os.path.exists(output_file_path):
            await message.answer("Ошибка: файл не был создан.")
            return
        try:
            input_file = FSInputFile(path=output_file_path)
            await message.answer_photo(input_file, caption="Выложи картинку в стори и пришли скрин")
        except Exception:
            await message.answer("Не удалось отправить фото. Пожалуйста, попробуй снова.")
            return

    except Exception:
        await message.answer("Произошла ошибка при обработке изображения. Пожалуйста, попробуйте снова.")
        return
    await state.set_state(AddResult_1.story_1)


@user_router.message(AddResult_1.frame_1)
async def frame_1_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, отправь изображение заново")


@user_router.message(AddResult_1.story_1, or_f(F.photo))
async def add_story_1(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(story_1=message.photo[-1].file_id)

    await state.update_data(date_1=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    is_result_exist = await get_result_unique(session, telegram_id)
    if is_result_exist is False:
        try:
            await add_result_for_user(session, telegram_id, data)
            await message.answer("Первый день есть!\nНо расслабляться рано - жду тебя завтра."
                                 , reply_markup=DAY2_KB, parse_mode='Markdown')
            await message.answer("Нажми команду /day_2 или кнопку, чтобы добавить вторую пробежку",
                                 reply_markup=DAY2_KB)

        except Exception as e:
            await message.answer(
                f"Данные не сохранены. Проверьте, что в ваш телеграм аккаунт введено имя пользователя, "
                f"по нему потом будет составляться турнирная таблица."
                f"\nДобавьте имя пользователя в профиле и попробуйте снова.", reply_markup=DAY1_KB)
            await state.clear()
    elif is_result_exist is True:
        try:
            await update_result1_for_user(session, telegram_id, data)
            await message.answer("Данные первого дня изменены!\nЖду тебя завтра.", reply_markup=DAY2_KB,
                                 parse_mode='Markdown')
            await message.answer("Нажми команду /day_2 или кнопку, чтобы добавить вторую пробежку",
                                 reply_markup=DAY2_KB)

        except Exception as e:
            await message.answer(
                f"Данные не сохранены. Проверьте, что в ваш телеграм аккаунт введено имя пользователя, "
                f"по нему потом будет составляться турнирная таблица."
                f"\nДобавьте имя пользователя в профиле и попробуйте снова.", reply_markup=DAY1_KB)
            await state.clear()
    await state.clear()


@user_router.message(AddResult_1.story_1)
async def story_1_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, отправь изображение заново")


"""Запись второго дня челленджа"""


@user_router.message(StateFilter(None), or_f(Command("day_2"), F.text == "Добавить результаты второго дня"))
async def add_result_2(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id

    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        await message.answer(f"Отправь скриншот пробежки любого бегового приложения или трекера, "
                             "где видно дистанцию второго дня (загрузи только одно изображение)")
        await state.set_state(AddResult_2.photo_2)
    else:
        await message.answer("Ты еще не зарегистрировался. "
                             "\nПопробуй начать сначала",
                             reply_markup=START_KB)


@user_router.message(AddResult_2.photo_2, or_f(F.photo, F.text == "."))
async def add_photo_2(message: types.Message, state: FSMContext):
    await state.update_data(photo_2=message.photo[-1].file_id)
    await message.answer("Какую дистанцию ты пробежал в километрах?"
                         "\nУкажи только число через точку(например 21.1)")
    await state.set_state(AddResult_2.distance_2)


@user_router.message(AddResult_2.photo_2)
async def photo_2_validation(message: types.Message):
    await message.answer("Отправь скриншот забега, только одно изображение.")


@user_router.message(AddResult_2.distance_2, or_f(F.text, F.text == "."))
async def add_distance_2(message: types.Message, state: FSMContext):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Пиши дистанцию через точку в километрах. "
                             "Другие символы не используй, пожалуйста."
                             "\n(Например 21.1)")
        return
    await state.update_data(distance_2=float(message.text))
    await message.answer("Отправь фото с пробежки и мы пришлем его в обработке в стилистике мероприятия."
                         "\nВыложи картинку в стори в любых соц сетях или мессенджерах.")
    await state.set_state(AddResult_2.frame_2)


@user_router.message(AddResult_2.distance_2)
async def distance_2_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, введите дистанцию заново")


@user_router.message(AddResult_2.frame_2, or_f(F.photo))
async def add_frame_2(message: types.Message, state: FSMContext):
    try:
        photo = message.photo[-1]  # Получаем наибольшую версию фото
        file_id = photo.file_id  # Получаем file_id для загрузки

        # Получаем файл с помощью bot.get_file()
        file = await message.bot.get_file(file_id)

        # Скачиваем файл
        photo_file = await message.bot.download_file(file.file_path)
        await message.answer("Пожалуйста, подожди, я добавляю рамку 🪄")

        # Открываем изображение с помощью Pillow
        image = Image.open(photo_file).convert("RGBA")

        output_file_path = add_frame(image, 2)

        if not os.path.exists(output_file_path):
            await message.answer("Ошибка: файл не был создан.")
            return
        try:
            input_file = FSInputFile(path=output_file_path)
            await message.answer_photo(input_file, caption="Выложи картинку в стори и пришли скрин")
        except Exception:
            await message.answer("Не удалось отправить фото. Пожалуйста, попробуй снова.")
            return


    except Exception:
        await message.answer("Произошла ошибка при обработке изображения. Пожалуйста, попробуй снова.")
        return
    await state.set_state(AddResult_2.story_2)


@user_router.message(AddResult_2.frame_2)
async def frame_2_validation(message: types.Message):
    await message.answer("Введены недопустимые данныее, отправь изображение заново")


@user_router.message(AddResult_2.story_2, or_f(F.photo))
async def add_story_2(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(story_2=message.photo[-1].file_id)
    await state.update_data(date_2=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    print(f'telegram_id = {telegram_id}, data = {data}')

    try:
        await update_result2_for_user(session, telegram_id, data)
        await message.answer("Второй день челленджа позади. Не сдавайся, и выходи на пробежку завтра. ",
                             reply_markup=DAY3_KB, parse_mode='Markdown'),
        await message.answer("Нажми команду /day_3 или кнопку, чтобы добавить третью пробежку",
                             reply_markup=DAY3_KB)

    except Exception as e:
        await message.answer(
            f"Данные не сохранены. Попробуйте снова.",
            reply_markup=DAY2_KB,
        )
        await state.clear()
    await state.clear()


@user_router.message(AddResult_2.story_2)
async def story_2_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, отправь изображение заново")


"""Запись третьего дня челленджа"""


@user_router.message(StateFilter(None), or_f(Command("day_3"), F.text == "Добавить результаты третьего дня"))
async def add_result_3(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id

    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        await message.answer(f"Отправь скриншот пробежки любого бегового приложения или трекера, "
                             f"где видно дистанцию третьего дня (загрузи только одно изображение)")
        await state.set_state(AddResult_3.photo_3)
    else:
        await message.answer("Ты еще не зарегистрировался. "
                             "\nПопробуй начать сначала",
                             reply_markup=START_KB)


@user_router.message(AddResult_3.photo_3, or_f(F.photo, F.text == "."))
async def add_photo_3(message: types.Message, state: FSMContext):
    await state.update_data(photo_3=message.photo[-1].file_id)
    await message.answer("Какую дистанцию ты пробежал в километрах?"
                         "\nУкажи только число через точку(например 21.1)")
    await state.set_state(AddResult_3.distance_3)


@user_router.message(AddResult_3.photo_3)
async def photo_3_validation(message: types.Message):
    await message.answer("Отправь скриншот забега, только одно изображение.")


@user_router.message(AddResult_3.distance_3, or_f(F.text, F.text == "."))
async def add_distance_3(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Пиши дистанцию через точку в километрах. "
                             "Другие символы не используй, пожалуйста."
                             "\n(Например 21.1)")
        return
    await state.update_data(distance_3=float(message.text))
    telegram_id = message.from_user.id
    total = await get_total_distance(session, telegram_id)
    result = total + float(message.text)
    await state.update_data(result=result)
    await message.answer("Отправь фото с пробежки и мы пришлем его в обработке в стилистике мероприятия."
                         "\nВыложи картинку в стори в любых соц сетях или мессенджерах.")
    await state.set_state(AddResult_3.frame_3)


@user_router.message(AddResult_3.distance_3)
async def distance_3_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, введи дистанцию заново")


@user_router.message(AddResult_3.frame_3, or_f(F.photo))
async def add_frame_3(message: types.Message, state: FSMContext):
    try:
        photo = message.photo[-1]  # Получаем наибольшую версию фото
        file_id = photo.file_id  # Получаем file_id для загрузки

        # Получаем файл с помощью bot.get_file()
        file = await message.bot.get_file(file_id)

        # Скачиваем файл
        photo_file = await message.bot.download_file(file.file_path)
        await message.answer("Пожалуйста, подожди, я добавляю рамку 🪄")

        # Открываем изображение с помощью Pillow
        image = Image.open(photo_file).convert("RGBA")

        output_file_path = add_frame(image, 3)
        if not os.path.exists(output_file_path):
            await message.answer("Ошибка: файл не был создан.")
            return
        try:
            input_file = FSInputFile(path=output_file_path)
            await message.answer_photo(input_file, caption="Выложи картинку в стори и пришли скрин")
        except Exception:
            await message.answer("Не удалось отправить фото. Пожалуйста, попробуй снова.")
            return

    except Exception:
        await message.answer("Произошла ошибка при обработке изображения. Пожалуйста, попробуй снова.")
        return
    await state.set_state(AddResult_3.story_3)


@user_router.message(AddResult_3.frame_3)
async def frame_3_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, отправь изображение заново")


@user_router.message(AddResult_3.story_3, or_f(F.photo, F.text == "."))
async def add_story_3(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(story_3=message.photo[-1].file_id)
    await state.update_data(date_3=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    print(f'telegram_id = {telegram_id}, data = {data}')
    try:
        await update_result3_for_user(session, telegram_id, data)
        await message.answer("Поздравляем с завершением челленджа и ждем на следующем февральском этапе! ⚡️",
                             parse_mode='Markdown')
        await message.answer("Получи промокод на скидку 15% для себя и друга по команде /promo",
                             parse_mode='Markdown')
        await message.answer("Сомневаешься в правильности введеных результатов? "
                             "Это можно проверить по команде /result",
                             reply_markup=CHECK_KB)

    except Exception as e:
        await message.answer(
            f"Данные не сохранены. Попробуйте снова.",
            reply_markup=DAY3_KB,
        )
        await state.clear()
    await state.clear()


@user_router.message(AddResult_3.story_3)
async def story_3_validation(message: types.Message):
    await message.answer("Введены недопустимые данные, отправь изображение заново")


"""Вывод результатов"""


@user_router.message(StateFilter(None), or_f(Command("result"), F.text == "Показать мой результат"))
async def get_result(message: types.Message, session: AsyncSession):
    telegram_id = message.from_user.id
    distance = await get_user_distances(session, telegram_id)
    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        if distance[0] != 0:
            await message.answer(f"Дистанция первого дня: {distance[0]}")
        else:
            await message.answer(f"Я не вижу дистанцию первого дня. Загрузи трек еще раз /day_1 ")
        if distance[1] != 0:
            await message.answer(f"Дистанция второго дня: {distance[1]}")
        else:
            await message.answer(f"Я не вижу дистанцию второго дня. Загрузи трек еще раз /day_2 ")
        if distance[2] != 0:
            await message.answer(f"Дистанция третьего дня: {distance[2]}")
        else:
            await message.answer(f"Я не вижу дистанцию трерьего дня. Загрузи трек еще раз /day_3 ")
    else:
        await message.answer("Ты еще не зарегистрировался. "
                             "\nПопробуй начать сначала",
                             reply_markup=START_KB)


@user_router.message(StateFilter(None), or_f(Command("promo"), F.text == "Получить промокод"))
async def check_result(message: types.Message, session: AsyncSession):
    telegram_id = message.from_user.id
    check_result = await check_distances_filled(session, telegram_id)

    if check_result is False:
        await message.answer(f"Ты не выполнил все условия, чтобы получить промокод. "
                             f"Проверь, что все дни тренировок записаны, по команде /result",
                             reply_markup=CHECK_KB)
    else:
        promo_code = await get_promo_code(session, telegram_id)
        if promo_code == 'Promo code not found':
            await message.answer(f"Упс, закончились промокоды 😔"
                                 f"\nНапиши пожалуйста на почту topigacup@topliga.ru и мы сделаем новый.")
        else:
            await message.answer(f"Поздравляю! Вот твой промокод на скидку 15% для регистрации на RAY Sirius Autodrom:"
                                 f"\n*{promo_code}*"
                                 f"\nПромокод сработает 2 раза: можно пригласить друга и бежать командой!",
                                 parse_mode='Markdown')

# """код отмены"""
#
#
# @user_router.message(StateFilter('*'), or_f(Command("cancel"), F.text.lower() == "отмена"))
# async def cancel_handler(message: types.Message, state: FSMContext) -> None:
#     await state.clear()
#     await message.answer("Действия отменены", reply_markup=ALL_KB)
#
#
# dp.message.register(cancel_handler, Command("cancel"), StateFilter('*'))
