import asyncio
from aiogram import Bot, Dispatcher

# # from aiogram.utils import executor

import os
from dotenv import load_dotenv, find_dotenv, dotenv_values

# from dependencies import Dependencies

from middlewares.db import DataBaseSession
from database.engine import create_db, drop_db, session_maker

# from routers import admin_router, user_router
from handlers.user_private import user_router
from handlers.admin_private import admin_router


load_dotenv(find_dotenv())

ALLOWED_UPDATES = ['message, edited_message']

config = dotenv_values('.env')
api_token = config['TELEGRAM_API_TOKEN']

bot = Bot(token=api_token)
dp = Dispatcher(bot=bot)


# bot = Dependencies.bot(token=api_token)
# dp = Dependencies.dispatcher(bot=bot)

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
    # admin_router.message(MyForm.message)(handle_message_for_broadcast, bot=bot)
    # await dp.wait_idle()


asyncio.run(main())


