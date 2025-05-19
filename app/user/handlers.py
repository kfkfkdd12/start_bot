from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.types.input_file import FSInputFile
from pathlib import Path

import app.database.db_queries as qu
from . import user_kb as kb
from app.bot import bot

r = Router()

@r.message(CommandStart())
async def start(mes: Message, command: CommandStart):
    await qu.register_user(mes.from_user.id, mes.from_user.username, command.args)
    user = await qu.get_user(mes.from_user.id)
    await mes.answer("Приветствую в боте", reply_markup=kb.main)


@r.message(F.text == "🌟Получить звезды")
async def get_stars(mes: Message):
    bot_info = await bot.get_me()
    invite_count = await qu.get_invite_count(mes.from_user.id)
    invite_link = f"https://t.me/{bot_info.username}?start={mes.from_user.id}"
    text = (
        "+ 3 ⭐️ за каждого приглашенного тобой пользователя 🔥\n\n"
        "👫 Приглашайте знакомых и друзей, а также делитесь своей ссылкой в различных чатах!\n\n"
        f"🔗 Ваша пригласительная ссылка:\n{invite_link}\n\n"
        f"🏃‍♀️ Переходы по вашей ссылке: {invite_count}"
    )
    
    # Путь к фото
    photo_path = Path(__file__).parent.parent / "picture" / "job_stars.jpg"
    
    # Получаем клавиатуру с кнопкой шаринга
    share_keyboard = await kb.get_share_keyboard(mes.from_user.id)
    
    # Отправляем фото с подписью и кнопкой шаринга
    await mes.answer_photo(
        photo=FSInputFile(photo_path),
        caption=text,
        reply_markup=share_keyboard
    )
        



