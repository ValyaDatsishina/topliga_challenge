import asyncio
from typing import List, Optional
from aiogram import Bot, Dispatcher
import logging
import os
from dotenv import load_dotenv, find_dotenv, dotenv_values

from middlewares.db import DataBaseSession
from database.engine import create_db, drop_db, session_maker
from handlers.user_private import user_router
from handlers.admin_private import admin_router

# Конфигурация логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Отключение лишних логов
for logger_name in ['sqlalchemy.engine', 'aiogram']:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

class BotConfig:
    def __init__(self):
        # Чтение секретов из файлов
        try:
            with open('/run/secrets/telegram_token', 'r') as f:
                self.api_token: str = f.read().strip()
            with open('/run/secrets/db_url', 'r') as f:
                os.environ['DATABASE_URL'] = f.read().strip()
            with open('/run/secrets/user_ids', 'r') as f:
                user_ids = f.read().strip().split(',')
                self.admin_ids: List[int] = [int(uid) for uid in user_ids if uid]
        except FileNotFoundError as e:
            # Если файлы секретов не найдены, пробуем читать из .env
            load_dotenv(find_dotenv())
            self.config = dotenv_values('.env')
            self.api_token = self.config.get('TELEGRAM_API_TOKEN', '')
            self.admin_ids = [
                int(os.getenv(f'USER_ID_{i}')) 
                for i in range(5) 
                if os.getenv(f'USER_ID_{i}')
            ]
            if not self.api_token:
                raise ValueError("No Telegram API token found in secrets or .env")

async def on_startup(bot: Bot, run_param: bool = False) -> None:
    if run_param:
        await drop_db()
    await create_db()

async def main() -> None:
    # Инициализация конфигурации
    config = BotConfig()
    
    # Создание экземпляров бота и диспетчера
    bot = Bot(token=config.api_token)
    dp = Dispatcher()
    
    # Установка списка администраторов
    bot.my_admins_list = config.admin_ids
    
    # Регистрация роутеров
    dp.include_routers(admin_router, user_router)
    
    # Регистрация middleware и startup handler
    dp.startup.register(on_startup)
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    
    # Запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
