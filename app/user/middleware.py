from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from ..database import db_queries as qu

logger = logging.getLogger(__name__)

class AdPostMiddleware(BaseMiddleware):
    """Middleware для показа рекламных постов при нажатии кнопок главного меню"""
    
    # Список текстов кнопок, на которые реагирует middleware
    MAIN_MENU_BUTTONS = {
        "🌟 Получить звезды",
        "👤 Профиль",
        "📚 Задания",
        "🗒 Отзывы",
        "🏅 Промокод",
        "💳 Вывести",
        "📕 Помощь"
    }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, что это сообщение и оно содержит текст
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)
            
        # Проверяем, что текст сообщения соответствует кнопкам главного меню
        if event.text not in self.MAIN_MENU_BUTTONS:
            return await handler(event, data)
            
        # Получаем случайный рекламный пост
        ad_post = await qu.get_random_ad_post()
        if not ad_post:
            return await handler(event, data)
            
        # Создаем клавиатуру из строки с кнопками
        keyboard = None
        if ad_post.url:
            buttons = []
            # Разбиваем строку на пары "текст - ссылка"
            button_pairs = [pair.strip() for pair in ad_post.url.split(',')]
            for pair in button_pairs:
                if ' - ' in pair:
                    text, url = pair.split(' - ', 1)
                    buttons.append([InlineKeyboardButton(text=text.strip(), url=url.strip())])
            if buttons:
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Отправляем рекламный пост
        try:
            await event.answer(
                text=ad_post.text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке рекламного поста: {e}")
            
        # Продолжаем обработку оригинального сообщения
        return await handler(event, data) 