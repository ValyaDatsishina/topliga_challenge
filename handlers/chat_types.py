from typing import List, Union
from aiogram.filters import Filter
from aiogram import Bot, types
from aiogram.enums import ChatType


class BaseFilter(Filter):
    """Базовый класс для фильтров"""
    async def __call__(self, *args, **kwargs) -> bool:
        raise NotImplementedError


class ChatTypeFilter(BaseFilter):
    """Фильтр для проверки типа чата"""
    def __init__(self, chat_types: Union[List[str], List[ChatType]]) -> None:
        self.chat_types = [
            chat_type if isinstance(chat_type, ChatType) else ChatType(chat_type)
            for chat_type in chat_types
        ]

    async def __call__(self, message: types.Message) -> bool:
        return message.chat.type in self.chat_types


class IsAdmin(BaseFilter):
    """Фильтр для проверки прав администратора"""
    async def __call__(self, message: types.Message, bot: Bot) -> bool:
        if not hasattr(bot, 'my_admins_list'):
            return False
        return message.from_user.id in bot.my_admins_list


class IsPrivate(ChatTypeFilter):
    """Фильтр для приватных чатов"""
    def __init__(self) -> None:
        super().__init__([ChatType.PRIVATE])


class IsGroup(ChatTypeFilter):
    """Фильтр для групповых чатов"""
    def __init__(self) -> None:
        super().__init__([ChatType.GROUP, ChatType.SUPERGROUP])
