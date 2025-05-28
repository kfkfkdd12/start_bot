from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton,
                            ReplyKeyboardMarkup, KeyboardButton)
from urllib.parse import quote
from ..bot import bot

from config import Config

# Словарь для сопоставления ID подарка с его стоимостью
GIFT_PRICES = {
    5170233102089322756: 15,  # 🧸
    5170145012310081615: 15,  # 💝
    5168103777563050263: 25,  # 🌹
    5170250947678437525: 25,  # 🎁
    6028601630662853006: 50,  # 🍾
    5170564780938756245: 50,  # 🚀
    5170314324215857265: 50,  # 💐
    5170144170496491616: 50,  # 🎂
    5168043875654172773: 100, # 🏆
    5170690322832818290: 100, # 💍
}

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
    [KeyboardButton(text="🌟 Получить звезды")],
    [KeyboardButton(text="👤 Профиль"),
      KeyboardButton(text="📚 Задания"), 
      KeyboardButton(text="🗒 Отзывы")],
    [KeyboardButton(text="🏅 Промокод"), 
     KeyboardButton(text="💳 Вывести"),
       KeyboardButton(text="📕 Помощь")],
    # [KeyboardButton(text="Другие проекты")],
], resize_keyboard=True)


profile = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🌟 Пополнить депозит", callback_data="deposit")]
])


reviews = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💬 Наш чат", url=Config.CHAT_URL)],
    [InlineKeyboardButton(text=" Наши отзывы", url=Config.REVIEWS_URL)]
])

promo_cancel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_promo")]
])


withdraw = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💫 Вывести Stars", callback_data="withdraw")]
])

withdraw_gift = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧸 15⭐", callback_data="gift_5170233102089322756"),
     InlineKeyboardButton(text="💝 15⭐", callback_data="gift_5170145012310081615")],
    [InlineKeyboardButton(text="🌹 25⭐", callback_data="gift_5168103777563050263"),
     InlineKeyboardButton(text="🎁 25⭐", callback_data="gift_5170250947678437525")],
    [InlineKeyboardButton(text="🍾 50⭐", callback_data="gift_6028601630662853006"),
     InlineKeyboardButton(text="🚀 50⭐", callback_data="gift_5170564780938756245")],
    [InlineKeyboardButton(text="💐 50⭐", callback_data="gift_5170314324215857265"),
     InlineKeyboardButton(text="🎂 50⭐", callback_data="gift_5170144170496491616")],
    [InlineKeyboardButton(text="🏆 100⭐", callback_data="gift_5168043875654172773"),
     InlineKeyboardButton(text="💍 100⭐", callback_data="gift_5170690322832818290")],
    [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_withdraw")]
])

help_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❓ Сколько ждать вывода?", callback_data="withdraw_time")],
        [InlineKeyboardButton(text="❓ Почему не засчитало друга?", callback_data="friend_not_counted")]
    ]
)



# other_projects = InlineKeyboardMarkup(inline_keyboard=[
#     [InlineKeyboardButton(text="🌟 Купить звезды", url="https://t.me/ynpershop_bot?start=RLfWA9Zwmk")]
# ])

