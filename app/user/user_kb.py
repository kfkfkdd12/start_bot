from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                            ReplyKeyboardMarkup, KeyboardButton)
from urllib.parse import quote
from ..bot import bot

async def get_share_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой шаринга"""
    bot_info = await bot.get_me()
    share_text = (
        "🌟 Приглашайте друзей и зарабатывайте вместе с StarsBot! 🌟\n\n"
        "Хотите зарабатывать без вложений и тратить на это минимум времени? Теперь это возможно!✧\n\n"
        "👫 Приглашайте своих друзей, знакомых и коллег в StarsBot и получайте 2⭐️ за каждого приглашенного пользователя!\n"
        "Не упустите свой шанс! Делитесь своей ссылкой со знакомыми, в чатах, социальных сетях! 💬\n\n"
        "🔗 Заходи и зарабатывай:\n"
        f"https://t.me/{bot_info.username}?start={user_id}"
    )
    
    # Кодируем текст для URL
    encoded_text = quote(share_text)
    share_url = f"https://t.me/share/url?url={encoded_text}"
    
    keyboard = [
        [InlineKeyboardButton(text="📤 Поделиться с друзьями", url=share_url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🌟Получить звезды")],
    [KeyboardButton(text="👤Профиль"),
      KeyboardButton(text="📚Задания"), 
      KeyboardButton(text="🗒Отзывы")],
    [KeyboardButton(text="🏅Промокод"), 
     KeyboardButton(text="💳Вывести"),
       KeyboardButton(text="📕Помощь")],
], resize_keyboard=True)








