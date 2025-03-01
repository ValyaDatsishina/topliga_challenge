from typing import Dict, List, Optional, Tuple, Union
from aiogram.types import KeyboardButton, InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


class KeyboardFactory:
    @staticmethod
    def create_reply_keyboard(
        buttons: Union[List[str], Tuple[str, ...]],
        placeholder: Optional[str] = None,
        request_contact_index: Optional[int] = None,
        request_location_index: Optional[int] = None,
        sizes: Tuple[int, ...] = (2, 2)
    ) -> ReplyKeyboardMarkup:
        """
        Создает обычную клавиатуру с возможностью запроса контакта или локации
        """
        keyboard = ReplyKeyboardBuilder()

        for index, text in enumerate(buttons):
            if request_contact_index and request_contact_index == index:
                keyboard.add(KeyboardButton(text=text, request_contact=True))
            elif request_location_index and request_location_index == index:
                keyboard.add(KeyboardButton(text=text, request_location=True))
            else:
                keyboard.add(KeyboardButton(text=text))

        return keyboard.adjust(*sizes).as_markup(
            resize_keyboard=True,
            input_field_placeholder=placeholder
        )

    @staticmethod
    def create_inline_keyboard(
        buttons: Dict[str, str],
        sizes: Tuple[int, ...] = (2,),
        keyboard_type: str = 'mixed'
    ) -> InlineKeyboardMarkup:
        """
        Создает инлайн-клавиатуру с поддержкой callback, url или смешанных кнопок
        keyboard_type может быть: 'callback', 'url' или 'mixed'
        """
        keyboard = InlineKeyboardBuilder()

        for text, value in buttons.items():
            if keyboard_type == 'callback':
                keyboard.add(InlineKeyboardButton(text=text, callback_data=value))
            elif keyboard_type == 'url':
                keyboard.add(InlineKeyboardButton(text=text, url=value))
            else:  # mixed
                if '://' in value:
                    keyboard.add(InlineKeyboardButton(text=text, url=value))
                else:
                    keyboard.add(InlineKeyboardButton(text=text, callback_data=value))

        return keyboard.adjust(*sizes).as_markup()

    @staticmethod
    def create_list_keyboard(
        buttons: List[str],
        placeholder: Optional[str] = None,
        sizes: Tuple[int, ...] = (2, 2)
    ) -> ReplyKeyboardMarkup:
        """
        Создает клавиатуру из списка кнопок
        """
        keyboard = ReplyKeyboardBuilder()
        
        for text in buttons:
            keyboard.add(KeyboardButton(text=text))

        return keyboard.adjust(*sizes).as_markup(
            resize_keyboard=True,
            input_field_placeholder=placeholder
        )
