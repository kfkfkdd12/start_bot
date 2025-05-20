from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.types.input_file import FSInputFile
from pathlib import Path
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import app.database.db_queries as qu
from . import user_kb as kb
from app.bot import bot
from .user_kb import main, promo_cancel


r = Router()

class PromoCode(StatesGroup):
    waiting_for_code = State()

@r.message(CommandStart())
async def start(mes: Message, command: CommandStart):
    await qu.register_user(mes.from_user.id, mes.from_user.username, command.args)
    await mes.answer("Приветствую в боте", reply_markup=kb.main)


@r.message(F.text == "🌟 Получить звезды")
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
    photo_path = Path(__file__).parent.parent / "picture" / "job_stars.jpg"
    share_keyboard = await kb.get_share_keyboard(mes.from_user.id)
    await mes.answer_photo(
        photo=FSInputFile(photo_path),
        caption=text,
        reply_markup=share_keyboard
    )
        

@r.message(F.text == "👤 Профиль")
async def profile(mes: Message):
    user = await qu.get_user(mes.from_user.id)
    text =(f"⭐ Ваш ID - {mes.from_user.id}\n"
        f"👫 TG: @{mes.from_user.username or 'Неизвестен'}\n\n"
        f"💵 Депозит — {user.deposit:.2f} ⭐\n"
        f"💰 Баланс — {user.balans:.2f} ⭐\n")
    photo_path = Path(__file__).parent.parent / "picture" / "profile.jpg"
    await mes.answer_photo(
        photo=FSInputFile(photo_path),
        caption=text,
        reply_markup=kb.profile
    )


@r.message(F.text == "🗒 Отзывы")
async def reviews(mes: Message):
    text = "📝 Для ознакомления с отзывами, пожалуйста, перейдите по следующей ссылке: "
    photo_path = Path(__file__).parent.parent / "picture" / "reviews.jpg"
    await mes.answer_photo(
        photo=FSInputFile(photo_path),
        caption=text,
        reply_markup=kb.reviews
    )

@r.message(F.text == "🏅 Промокод")
async def promo_start(message: Message, state: FSMContext):
    """Обработчик нажатия кнопки Промокод"""
    photo_path = Path(__file__).parent.parent / "picture" / "promo.jpg"
    await message.answer_photo(
        photo=FSInputFile(photo_path),
        caption="🏆 Введите промокод:",
        reply_markup=kb.promo_cancel
    )
    await state.set_state(PromoCode.waiting_for_code)

@r.message(PromoCode.waiting_for_code, F.text == "❌ Отменить")
async def cancel_promo(mes: Message, state: FSMContext):
    """Отмена ввода промокода"""
    await state.clear()
    await mes.delete()


@r.message(PromoCode.waiting_for_code)
async def process_promo_code(mes: Message, state: FSMContext):
    """Обработка введенного промокода"""
    promo_code = mes.text.strip().upper()  # Приводим к верхнему регистру
            # Получаем промокод из базы
    promo = await qu.get_promo_code( promo_code)
        
    if not promo:
            await mes.answer(
                "❌ Промокод не найден или недействителен",
                reply_markup=main
            )
            await state.clear()
            return
        
        # Пытаемся активировать промокод
    success = await qu.activate_promo_code(mes.from_user.id, promo)
        
    if success:
            await mes.answer(
                f"✅ Промокод успешно активирован!\n\n"
                f"🎁 Начислено: {promo.reward} ⭐\n"
                f"💫 Ваш баланс обновлен",
                reply_markup=main
        )
    else:
        # Проверяем причину неудачи
        if await qu.check_promo_activation(mes.from_user.id, promo.id):
                await mes.answer(
                    "❌ Вы уже активировали этот промокод",
                    reply_markup=main
                )
        else:
                await mes.answer(
                    "❌ Промокод больше не действителен (превышен лимит активаций)",
                    reply_markup=main
                )
    
    await state.clear()




