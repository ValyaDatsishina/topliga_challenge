import asyncio
from aiogram import Bot, Dispatcher
import logging


import os
from dotenv import load_dotenv, find_dotenv, dotenv_values

from middlewares.db import DataBaseSession
from database.engine import create_db, drop_db, session_maker

from handlers.user_private import user_router
from handlers.admin_private import admin_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)  # Установите уровень логирования для вашего приложения
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)  # Отключаем логи SQLAlchemy
logging.getLogger('aiogram').setLevel(logging.ERROR)  # Отключаем логи SQLAlchemy


load_dotenv(find_dotenv())

ALLOWED_UPDATES = ['message, edited_message']

config = dotenv_values('.env')
api_token = config['TELEGRAM_API_TOKEN']

bot = Bot(token=api_token)
dp = Dispatcher(bot=bot)

bot.my_admins_list = []
for i in range(0, 5):
    bot.my_admins_list.append(int(os.getenv(f'USER_ID_{i}')))

dp.include_router(admin_router)
dp.include_router(user_router)


async def on_startup(bot):
    run_param = False
    if run_param:
        await drop_db()

    await create_db()


async def main():
    dp.startup.register(on_startup)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
