from datetime import datetime

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.chat_types import ChatTypeFilter
from database.orm_query import add_user, update_user_1, update_user_2, update_user_3, get_user, \
    get_user_unique
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
    story_1 = State()
    date_1 = State()

    texts = {
        'AddResult_1:photo_1': 'Загрузите фото заново:',
        'AddResult_1:distance_1': 'Введите дистанцию в километрах',
        'AddResult_1:story_1': 'Загрузите фото заново:', }


class AddResult_2(StatesGroup):
    distance_2 = State()
    photo_2 = State()
    story_2 = State()
    date_2 = State()

    texts = {
        'AddResult_2:photo_2': 'Загрузите фото заново:',
        'AddResult_2:distance_2': 'Введите дистанцию в километрах',
        'AddResult_2:story_2': 'Загрузите фото заново:', }


class AddResult_3(StatesGroup):
    distance_3 = State()
    photo_3 = State()
    story_3 = State()
    date_3 = State()
    index = State()
    city = State()
    address = State()
    result = State()

    field_for_change = None

    texts = {
        'AddResult_3:photo_3': 'Загрузите фото заново:',
        'AddResult_3:distance_3': 'Введите дистанцию в километрах',
        'AddResult_3:story_3': 'Загрузите фото заново:',
        'AddResult_3:index': 'Введите индекс заново:',
        'AddResult_3:city': 'Введите город заново:',
        'AddResult_3:address': 'Введите адрес заново:',
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
        user = await get_user(session, telegram_id)
        await message.answer(f'Вы уже зарегистрированы!')
        if not user.distance_1:
            await message.answer(f'Но вы не добавили результаты первого дня челленджа.', reply_markup=DAY1_KB)
        elif not user.distance_2:
            await message.answer(f'Но вы не добавили результаты второго дня челленджа.', reply_markup=DAY2_KB)
        elif not user.distance_3:
            await message.answer(f'Но вы не добавили результаты третьего дня челленджа.', reply_markup=DAY3_KB)
        else:
            await message.answer(f"{user.name}, поздравляем вас с окончанием челленджа ☀️"
                                 f"\nВ первый день вы преодалели {user.distance_1} км"
                                 f"\nВо второй день: {user.distance_2} км"
                                 f"\nВ третий день: {user.distance_3} км"
                                 f"\nОбщий результат: {user.result} км"
                                 f"\nОтличный результат, так держать!")

    else:
        await message.answer(f'Мы рады видеть вас на заключительном челлендже ANTA Сочи Марафон!\n'
                             f'\nНапоминаем условия челленджа:'
                             f'\n1. Выходить на пробежку каждый день с 11 по 13 октября;'
                             f'\n2. Присылать трек пробежки в тот же день в этот чат-бот;'
                             f'\n3. Подписаться на [страницу VK спортивного бренда ANTA](https://vk.com/anta_official);'
                             f'\n4. Выкладывать сториз о пробежках в любых соц сетях или мессенджерах с текстом: '
                             f'*готовлюсь к ANTA Сочи Марафону*🌴', parse_mode='Markdown')
        await message.answer(
            f'Если вы допустили ошибку при вводе данных, нажмите /cancel и начните сначала.\n'
            f'\nВ меню, рядом со строчкой ввода текста, вы можете увидеть все доступные команды, '
            f'но просим вас добавлять записи тренировок по порядку, чтобы итоговый результат посчитался верно.')
        await message.answer(f'Для участия нужно зарегистрироваться. \nВведите ваше Имя')
        await state.set_state(AddUser.name)


@user_router.message(AddUser.name, or_f(F.text, F.text == "."))
async def add_name(message: types.Message, state: FSMContext):
    if '/' in message.text or 'зарегистрироваться' in message.text.lower():
        await message.answer(f'Введите Имя еще раз')
        return
    else:
        await state.update_data(name=message.text)
        user = message.from_user
        await state.update_data(telegram_id=user.id)
        await state.update_data(telegram_login=user.username)
        # else:
        #     await state.update_data(telegram_login='неизвестный атлет')
        await message.answer("Введите номер телефона в формате 7хххххххххх (без '+')")
        await state.set_state(AddUser.phone)


@user_router.message(AddUser.name)
async def name_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите Имя заново")


@user_router.message(AddUser.phone, or_f(F.text, F.text == "."))
async def add_phone(message: types.Message, state: FSMContext):
    try:
        int(message.text)
        if len(message.text) != 11:
            raise Exception('incorrect phone number length')
    except ValueError:
        await message.answer("Введите номер телефона без дополнительных символов")

        return
    except Exception:
        await message.answer("Некорректная длина номер телефона, введите номер телефона еще раз")
        return
    await state.update_data(phone=message.text)

    await message.answer("Введите email")
    await state.set_state(AddUser.email)


@user_router.message(AddUser.phone)
async def phone_validation(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите номер телефона заново")


@user_router.message(AddUser.email, or_f(F.text, F.text == "."))
async def add_email(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(email=message.text)
    data = await state.get_data()
    try:
        await add_user(session, data)
        await message.answer("Отлично, вы зарегистированы!"
                             "\nВперед на пробежку! "
                             "Не забудьте записать трек тренировки, а также сделать сториз с текстом: "
                             "*готовлюсь к ANTA Сочи Марафону*"
                             "\nЕсли вы выкладываете историю в Instagram, отмечайте @topligarun.",
                             reply_markup=DAY1_KB, parse_mode='Markdown')

        await message.answer("Нажмите команду /day_1 или кнопку, чтобы добавить первую пробежку",
                             reply_markup=DAY1_KB)

    except Exception as e:
        await message.answer(
            f"Данные не сохранены. Проверьте, что в ваш телеграм аккаунт введено имя пользователя, "
            f"по нему потом будет составляться турнирная таблица."
            f"\nДобавьте имя пользователя в профиле и попробуйте снова.",
            reply_markup=START_KB,
        )
        await state.clear()

    await state.clear()


@user_router.message(AddUser.email)
async def email_validation(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите почту заново")


"""Запись первого дня челленджа"""


@user_router.message(StateFilter(None), or_f(Command("day_1"), F.text == "Добавить результаты первого дня"))
async def add_result_1(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        await message.answer(f"Отправьте скриншот пробежки первого дня (загрузите только 1 изображение)")
        await state.set_state(AddResult_1.photo_1)
    else:
        await message.answer("Вы еще не зарегистрировались. "
                             "\nПопробуйте начать сначала",
                             reply_markup=START_KB)


@user_router.message(AddResult_1.photo_1, or_f(F.photo, F.text == "."))
async def add_photo_1(message: types.Message, state: FSMContext):
    await state.update_data(photo_1=message.photo[-1].file_id)
    await message.answer("Какую дистанцию вы пробежали в километрах?"
                         "\nУкажите только число через точку(например 21.1)")
    await state.set_state(AddResult_1.distance_1)


@user_router.message(AddResult_1.photo_1)
async def photo_1_validation(message: types.Message):
    await message.answer("Отправьте скриншот забега, только одно изображение.")


@user_router.message(AddResult_1.distance_1, or_f(F.text, F.text == "."))
async def add_distance_1(message: types.Message, state: FSMContext):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Пишите дистанцию через точку в километрах. "
                             "Другие символы не используйте, пожалуйста."
                             "\n(Например 21.1)")
        return
    await state.update_data(distance_1=float(message.text))
    await message.answer("Отправьте скриншот сториз о пробежке первого дня."
                         "\nВы можете выложить сториз о подготовке к ANTA Сочи Марафону "
                         "в любых соц сетях или мессенджерах.")
    await state.set_state(AddResult_1.story_1)


@user_router.message(AddResult_1.distance_1)
async def distance_1_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите дистанцию заново")


@user_router.message(AddResult_1.story_1, or_f(F.photo))
async def add_story_1(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(story_1=message.photo[-1].file_id)
    await state.update_data(date_1=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    print(f'telegram_id = {telegram_id}, data = {data}')

    try:
        await update_user_1(session, telegram_id, data)
        await message.answer("Первый день есть! \nДарим вам промокод на скидку для ваших друзей - "
                             "приезжайте на старт командой ⚡️ "
                             "Выкладывайте его в стори с фото пробежки завтра.\n *START*", reply_markup=DAY2_KB,
                             parse_mode='Markdown')
        await message.answer("Нажмите команду /day_2 или кнопку, чтобы добавить вторую пробежку",
                             reply_markup=DAY2_KB)

    except Exception as e:
        await message.answer(
            f"Данные не сохранены. Проверьте, что в ваш телеграм аккаунт введено имя пользователя, "
            f"по нему потом будет составляться турнирная таблица."
            f"\nДобавьте имя пользователя в профиле и попробуйте снова.",
            reply_markup=DAY1_KB,
        )
        await state.clear()
    await state.clear()


@user_router.message(AddResult_1.story_1)
async def story_1_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, отправьте изображение заново")


"""Запись второго дня челленджа"""


@user_router.message(StateFilter(None), or_f(Command("day_2"), F.text == "Добавить результаты второго дня"))
async def add_result_2(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id

    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        await message.answer(f"Отправьте скриншот пробежки второго дня (загрузите только 1 изображение)")
        await state.set_state(AddResult_2.photo_2)
    else:
        await message.answer("Вы еще не зарегистрировались. "
                             "\nПопробуйте начать сначала",
                             reply_markup=START_KB)


@user_router.message(AddResult_2.photo_2, or_f(F.photo, F.text == "."))
async def add_photo_2(message: types.Message, state: FSMContext):
    await state.update_data(photo_2=message.photo[-1].file_id)
    await message.answer("Какую дистанцию вы пробежали в километрах?"
                         "\nУкажите только число через точку(например 21.1)")
    await state.set_state(AddResult_2.distance_2)


@user_router.message(AddResult_2.photo_2)
async def photo_2_validation(message: types.Message):
    await message.answer("Отправьте скриншот забега, только одно изображение.")


@user_router.message(AddResult_2.distance_2, or_f(F.text, F.text == "."))
async def add_distance_2(message: types.Message, state: FSMContext):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Пишите дистанцию через точку в километрах. "
                             "Другие символы не используйте, пожалуйста."
                             "\n(Например 21.1)")
        return
    await state.update_data(distance_2=float(message.text))
    await message.answer("Отправьте скриншот сториз о пробежке второго дня."
                         "\nВы можете выложить сториз о подготовке к ANTA Сочи Марафону "
                         "в любых соц сетях или мессенджерах.")
    await state.set_state(AddResult_2.story_2)


@user_router.message(AddResult_2.distance_2)
async def distance_2_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите дистанцию заново")


@user_router.message(AddResult_2.story_2, or_f(F.photo))
async def add_story_2(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(story_2=message.photo[-1].file_id)
    await state.update_data(date_2=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    print(f'telegram_id = {telegram_id}, data = {data}')

    try:
        await update_user_2(session, telegram_id, data)
        await message.answer("Второй день челленджа позади. Не сдавайтесь, и выходите на пробежку завтра. "
                             "\nНапоминаем: поделитесь скидочным промокодом на "
                             "марафон завтра в стори - бегите вместе с друзьями! ⚡️ "
                             "\n*START*", reply_markup=DAY3_KB,
                             parse_mode='Markdown'),
        await message.answer("Нажмите команду /day_3 или кнопку, чтобы добавить третью пробежку",
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
    await message.answer("Вы ввели не допустимые данные, отправьте изображение заново")


"""Запись третьего дня челленджа"""


@user_router.message(StateFilter(None), or_f(Command("day_3"), F.text == "Добавить результаты третьего дня"))
async def add_result_3(message: types.Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id

    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        await message.answer(f"Отправьте скриншот пробежки третьего дня (загрузите только 1 изображение)")
        await state.set_state(AddResult_3.photo_3)
    else:
        await message.answer("Вы еще не зарегистрировались. "
                             "\nПопробуйте начать сначала",
                             reply_markup=START_KB)


@user_router.message(AddResult_3.photo_3, or_f(F.photo, F.text == "."))
async def add_photo_3(message: types.Message, state: FSMContext):
    await state.update_data(photo_3=message.photo[-1].file_id)
    await message.answer("Какую дистанцию вы пробежали в километрах?"
                         "\nУкажите только число через точку(например 21.1)")
    await state.set_state(AddResult_3.distance_3)


@user_router.message(AddResult_3.photo_3)
async def photo_3_validation(message: types.Message):
    await message.answer("Отправьте скриншот забега, только одно изображение.")


@user_router.message(AddResult_3.distance_3, or_f(F.text, F.text == "."))
async def add_distance_3(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        float(message.text)
    except ValueError:
        await message.answer("Пишите дистанцию через точку в километрах. "
                             "Другие символы не используйте, пожалуйста."
                             "\n(Например 21.1)")
        return
    await state.update_data(distance_3=float(message.text))
    telegram_id = message.from_user.id
    user = await get_user(session, telegram_id)
    if user.distance_1 and user.distance_2:
        result = user.distance_1 + user.distance_2 + float(message.text)
        await state.update_data(result=result)
        print(f'result={result}')
    elif user.distance_1:
        result = user.distance_1 + float(message.text)
        await state.update_data(result=result)
        print(f'result={result}')
    elif user.distance_2:
        result = user.distance_2 + float(message.text)
        await state.update_data(result=result)
        print(f'result={result}')
    else:
        await state.update_data(result=float(message.text))
        print(f'result={float(message.text)}')
    await message.answer("Отправьте скриншот сториз о пробежке третьего дня."
                         "\nВы можете выложить сториз о подготовке к ANTA Сочи Марафону "
                         "в любых соц сетях или мессенджерах.")
    await state.set_state(AddResult_3.story_3)


@user_router.message(AddResult_3.distance_3)
async def distance_3_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите дистанцию заново")


@user_router.message(AddResult_3.story_3, or_f(F.photo, F.text == "."))
async def add_story_3(message: types.Message, state: FSMContext):
    await state.update_data(story_3=message.photo[-1].file_id)
    await message.answer("Ура, челлендж завершен!")
    await message.answer(f"Готовы получить заслуженный приз? Необходимо заполнить данные для отправки открытки.\n"
                         f"\nПожалуйста, проверьте правильность введенного индекса и адреса, это очень важно."
                         f"\nЕсли вы допустили ошибку при вводе данных, напишите /cancel и начните сначала.")
    await message.answer(f"Введите ваш почтовый индекс.")
    await state.set_state(AddResult_3.index)

    @user_router.message(AddResult_3.story_3)
    async def story_3_validation(message: types.Message):
        await message.answer("Вы ввели не допустимые данные, отправьте изображение заново")


@user_router.message(AddResult_3.index, or_f(F.text, F.text == "."))
async def add_index(message: types.Message, state: FSMContext):
    try:
        int(message.text)
    except ValueError:
        await message.answer("Введите индекс без дополнительных символов и пробелов")
        return
    await state.update_data(index=message.text)
    await message.answer("Напишите ваш город")
    await state.set_state(AddResult_3.city)


@user_router.message(AddResult_3.index)
async def index_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите индекс заново")


@user_router.message(AddResult_3.city, or_f(F.text, F.text == "."))
async def add_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Напишите ваш адрес, и не забудьте указать номер квартиру. "
                         "Иначе открытка вас не найдет 😊")
    await state.set_state(AddResult_3.address)


@user_router.message(AddResult_3.city)
async def city_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите город заново")


@user_router.message(AddResult_3.address, or_f(F.text, F.text == "."))
async def add_address(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(address=message.text)
    await state.update_data(date_3=datetime.now())
    telegram_id = int(message.from_user.id)
    data = await state.get_data()
    print(f'telegram_id = {telegram_id}, data = {data}')

    try:
        await update_user_3(session, telegram_id, data)
        await message.answer("Поздравляем с завершением челленджа и до встречи на марафоне! 🌴"
                             "\nПриезжайте с друзьями - делитесь в соц сетях промокодом на скидку *START️*",
                             parse_mode='Markdown')
        await message.answer("Сомневаетесь в правильности введеных результатов? "
                             "Вы можете проверить его по команде /result",
                             reply_markup=CHECK_KB)


    except Exception as e:
        await message.answer(
            f"Данные не сохранены. Попробуйте снова.",
            reply_markup=DAY3_KB,
        )
        await state.clear()
    await state.clear()


@user_router.message(AddResult_3.address)
async def address_validation(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите адрес заново")


"""Вывод результатов"""


@user_router.message(StateFilter(None), or_f(Command("result"), F.text == "Показать мой результат"))
async def get_result_(message: types.Message, session: AsyncSession):
    telegram_id = message.from_user.id
    user = await get_user(session, telegram_id)
    is_user_exist = await get_user_unique(session, telegram_id)
    if is_user_exist:
        if user.distance_1:
            await message.answer(f"Дистанция первого дня: {user.distance_1}")
        else:
            await message.answer(f"Не видим дистанцию первого дня. Загрузите трек еще раз /day_1 ")
        if user.distance_2:
            await message.answer(f"Дистанция второго дня: {user.distance_2}")
        else:
            await message.answer(f"Не видим дистанцию второго дня. Загрузите трек еще раз /day_2 ")
        if user.distance_3:
            await message.answer(f"Дистанция третьего дня: {user.distance_3}")
        else:
            await message.answer(f"Не видим дистанцию трерьего дня. Загрузите трек еще раз /day_3 ")
    else:
        await message.answer("Вы еще не зарегистрировались. "
                             "\nПопробуйте начать сначала",
                             reply_markup=START_KB)

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
