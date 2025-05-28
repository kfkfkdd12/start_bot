from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.types.input_file import FSInputFile
from pathlib import Path
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

import app.database.db_queries as qu
from . import user_kb as kb
from app.bot import bot
from .user_kb import main, promo_cancel, help_kb
from config import Config
from app.servise.subscribes_service import subscribes_service
from .middleware import AdPostMiddleware

logger = logging.getLogger(__name__)

r = Router()
# Подключаем middleware для рекламных постов
r.message.middleware(AdPostMiddleware())

class PromoCode(StatesGroup):
    waiting_for_code = State()

@r.message(CommandStart())
async def start(mes: Message, command: CommandStart):
    # Регистрируем пользователя
    await qu.register_user(mes.from_user.id, mes.from_user.username, command.args)
    
    # Получаем активные каналы
    channels = await qu.get_active_sponsor_channels()
    
    # Если нет активных каналов, сразу показываем стартовое сообщение
    if not channels:
        await mes.answer(
            "🌟 Добро пожаловать в StarsBot! 🌟\n\n"
            "Вы можете начать пользоваться ботом прямо сейчас!",
            reply_markup=kb.main
        )
        return
    
    # Создаем сообщение для подписки
    text = (
   """
<b>⭐️ПОЛУЧАЙ ЗВЕЗДЫ БЕСПЛАТНО⭐️</b>

<b>Получай 3 звезды абсолютно бесплатно за каждого приглашенного друга и задания⚡️</b>

<b><u>Чтобы активировать бота:</u></b>
<blockquote>1️⃣ Подпишись на каналы👇 (это займет 5 секунд).
2️⃣ Нажми «Я подписался✅»</blockquote>
   """
    )
    
    # Создаем клавиатуру с кнопками каналов
    keyboard = []
    for channel in channels:
        # Если channel_id == 0, добавляем канал без проверки подписки
        if channel.channel_id == 0:
            keyboard.append([InlineKeyboardButton(
                text=channel.button_name or channel.name,  # Используем button_name если есть, иначе name
                url=channel.url
            )])
        else:
            # Для остальных каналов проверяем подписку
            is_subscribed = await subscribes_service.is_user_subscribed(mes.from_user.id, channel.channel_id)
            if not is_subscribed:
                keyboard.append([InlineKeyboardButton(
                    text=channel.button_name or channel.name,  # Используем button_name если есть, иначе name
                    url=channel.url
                )])
    
    # Добавляем кнопку проверки только если есть неподписанные каналы
    if keyboard:
        keyboard.append([InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscriptions"
        )])
        # Отправляем сообщение с фото и кнопками, убирая reply-клавиатуру
        photo_path = Path(__file__).parent.parent / "picture" / "start.jpg"
        await mes.answer_photo(
            photo=FSInputFile(photo_path),
            caption=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        # Убираем reply-клавиатуру
        await mes.answer(
            "⚠️ Для продолжения необходимо подписаться на каналы",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        # Если пользователь уже подписан на все каналы
        await mes.answer(
            "✅ Спасибо за подписку! Вы можете пользоваться ботом.",
            reply_markup=kb.main
        )

@r.callback_query(F.data == "check_subscriptions")
async def check_subscriptions(callback: CallbackQuery):
    """Проверяет подписки пользователя на каналы"""
    channels = await qu.get_active_sponsor_channels()
    not_subscribed = []
    
    # Проверяем каждый канал через сервис
    for channel in channels:
        is_subscribed = await subscribes_service.is_user_subscribed(callback.from_user.id, channel.channel_id)
        if not is_subscribed:
            not_subscribed.append(channel)
    
    if not_subscribed:
        # Создаем клавиатуру только с неподписанными каналами
        keyboard = []
        for channel in not_subscribed:
            keyboard.append([InlineKeyboardButton(
                text=channel.button_name or channel.name,  # Используем button_name если есть, иначе name
                url=channel.url
            )])
        keyboard.append([InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscriptions"
        )])
        
        await callback.answer(
            "❌ Вы подписались не на все каналы!",
            show_alert=True
        )
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await callback.message.delete()
        await qu.update_user_op_status(callback.from_user.id, True)
        # Показываем главное меню только после успешной проверки подписок
        await callback.message.answer(
            "✅ Спасибо за подписку! Теперь вы можете пользоваться ботом.",
            reply_markup=kb.main
        )

@r.message(F.text == "🌟 Получить звезды")
async def get_stars(mes: Message):
    bot_info = await bot.get_me()
    invite_count = await qu.get_invite_count(mes.from_user.id)
    invite_link = f"https://t.me/{bot_info.username}?start={mes.from_user.id}"
    reward = await qu.get_current_referral_reward()
    text = (
        f"+ {reward} ⭐️ за каждого приглашенного тобой пользователя 🔥\n\n"
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

@r.callback_query   (PromoCode.waiting_for_code, F.data == "cancel_promo")
async def cancel_promo(callback_query: CallbackQuery, state: FSMContext):
    """Отмена ввода промокода"""
    await callback_query.message.delete()
    await state.clear()


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


@r.message(F.text == "💳 Вывести")
async def withdraw(mes: Message):
    text = "Для вывода ⭐️ Stars нажмите кнопку ниже:👇"
    photo_path = Path(__file__).parent.parent / "picture" / "withdraw.jpg"
    await mes.answer_photo(
        photo=FSInputFile(photo_path),
        caption=text,
        reply_markup=kb.withdraw
    )


@r.callback_query(F.data == "withdraw")
async def withdraw_callback(callback_query: CallbackQuery):
    user = await qu.get_user(callback_query.from_user.id)
    await callback_query.message.delete()
    if user.balans < 15:
        await callback_query.message.answer("✍️ Минимальная сумма вывода: 15 ⭐️\n\n<b>❗️ У вас пока не хватает Баланса для вывода!</b>\n\n🏷️ Заработайте больше 15 Старс и сможете вывести")
    else:
        await callback_query.message.answer("<i>Выберите подарок для вывода ниже👇</i>", reply_markup=kb.withdraw_gift)

@r.callback_query   (F.data == "cancel_withdraw")
async def cancel_promo(callback_query: CallbackQuery):
    """Отмена ввода промокода"""
    await callback_query.message.delete()

@r.callback_query(F.data.startswith("gift_"))
async def process_gift_withdrawal(callback_query: CallbackQuery):
    """Обработка вывода подарка"""
    try:
        # Получаем ID подарка из callback_data
        gift_id = int(callback_query.data.split("_")[1])
        
        # Получаем стоимость подарка
        gift_price = kb.GIFT_PRICES.get(gift_id)
            
        # Получаем пользователя для проверки
        user = await qu.get_user(callback_query.from_user.id)

        # Проверяем баланс
        if user.balans < gift_price:
            await callback_query.answer(
                f"❌ Недостаточно звезд!\n\n"
                f"💰 Ваш баланс: {user.balans} ⭐\n"
                f"💫 Стоимость подарка: {gift_price} ⭐",
                show_alert=True
            )
            return
            
        # Обрабатываем вывод подарка
        success, new_balance = await qu.process_gift_withdrawal(callback_query.from_user.id, gift_price)
        
        if not success:
            await callback_query.answer("❌ Ошибка при обработке вывода", show_alert=True)
            return
        
        # Отправляем сообщение пользователю
        await callback_query.message.edit_text(
            f"✅ Спасибо за вывод!\n\n"
            f"🎁 Подарок успешно отправлен\n"
            f"💫 Списано: {gift_price} ⭐\n"
            f"💰 Остаток баланса: {new_balance} ⭐"
        )
        
        # Отправляем уведомление в канал логов
        await notify_admin_about_withdraw(user, gift_id)
        
    except Exception as e:
        logger.error(f"Ошибка при выводе подарка: {e}")
        await callback_query.answer("❌ Произошла ошибка при обработке вывода", show_alert=True)

@r.message(F.text == "📕 Помощь")
async def help_command(mes: Message):
    help_text = (
        "📌 Правила использования StarsBot:\n\n"
        "Проблемы с выводом средств: решение найдено! 🤑\n\n"
        "Почему же не получается набрать минимальную сумму для вывода? 😕\n"
        "Есть несколько вариантов решения:\n\n"
        "1️⃣ Давайте подумаем о продвижении нашей ссылки! 📱 Вы можете поделиться ею с друзьями, а также просить перейти по ней людей с чатов или своего тг-канала.\n"
        "2️⃣ Или вы можете использовать один из интересных способов, которым пользуются другие пользователи: создавайте ролики в тик-ток и добавляйте свою личную ссылку в комментариях под тик-токами с схожей тематикой! 📹\n\n"
        "Почему не зачислилась сумма с моего баланса? 😕\n"
        "❓ Если вы поставили запрос на вывод, а деньги списались со счета, но не зачислились на аккаунт, то это означает, что ваш вывод отправлен администратору и ожидает подтверждения. 🤔\n\n"
        "Что делать дальше? 😊\n"
        "Если вы получите уведомление том, что вывод подтвержден, значит, в течении нескольких минут админ отправит его вам в виде подарка! 🎁 Пока это не произошло, просто подождите немного и проверьте свой аккаунт снова. 🕒️\n\n"
        "☀️ Приятного общения и удачи! 🤗"
    )
    await mes.answer(help_text, reply_markup=help_kb)

@r.callback_query(F.data == "withdraw_time")
async def withdraw_time_info(callback_query: CallbackQuery):
    await callback_query.answer(
        "📝 Ваша информация будет обработана и выведена администратором 🤖\n\n"
        "⏰ Это может занять от пары часов до 2 дней.\n\n"
        "🕰 Обычно же это занимает не более суток.",
        show_alert=True
    )

@r.callback_query(F.data == "friend_not_counted")
async def friend_not_counted_info(callback_query: CallbackQuery):
    await callback_query.answer(
        "🤖 Бот учитывает только новых пользователей.\n\n"
        "✍️ Кроме того, бонус за друга начисляется после того, как он подпишется на спонсоров нашего бота!",
        show_alert=True
    )

async def notify_admin_about_withdraw(user, gift_id):
    """Отправка уведомления админам о выводе подарка"""
    # Получаем эмодзи подарка из словаря GIFT_PRICES
    gift_emoji = {
        5170233102089322756: "🧸",  # 🧸
        5170145012310081615: "💝",  # 💝
        5168103777563050263: "🌹",  # 🌹
        5170250947678437525: "🎁",  # 🎁
        6028601630662853006: "🍾",  # 🍾
        5170564780938756245: "🚀",  # 🚀
        5170314324215857265: "💐",  # 💐
        5170144170496491616: "🎂",  # 🎂
        5168043875654172773: "🏆",  # 🏆
        5170690322832818290: "💍",  # 💍
    }.get(gift_id, "🎁")  # По умолчанию используем 🎁

    log_message = (
        f"🎁 Новый вывод подарка!\n\n"
        f"👤 Пользователь: {user.user_id}\n"
        f"🎯 ID подарка: {gift_id}\n"
        f"🎁 Подарок: {gift_emoji}"
    )
    
    # Создаем клавиатуру с кнопками связи и принятия
    contact_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💬 Связаться с пользователем",
                url=f"tg://user?id={user.user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"accept_withdraw_{user.user_id}_{gift_id}"
            )
        ]
    ])
    
    # Отправляем сообщение всем админам
    for admin_id in Config.ADMIN_IDS:
        try:
            # Сначала отправляем стикер
            await bot.send_sticker(
                admin_id,
                sticker=gift_id
            )
            # Затем отправляем сообщение
            await bot.send_message(
                admin_id,
                log_message,
                reply_markup=contact_kb
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")

@r.callback_query(F.data.startswith("accept_withdraw_"))
async def process_withdraw_accept(callback: CallbackQuery):
    """Обработка принятия вывода админом"""
    # Проверяем, является ли пользователь админом
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("У вас нет прав для этого действия", show_alert=True)
        return
    
    # Получаем данные из callback_data
    parts = callback.data.split("_")
    user_id = int(parts[2])  # Третье значение
    gift_id = parts[3]       # Четвертое значение
    
    # Обновляем сообщение админа
    new_text = (
        f"🎁 Вывод подарка выполнен!\n\n"
        f"👤 Пользователь: {user_id}\n"
        f"🎯 ID подарка: {gift_id}\n"
        f"✅ Выполнено: {callback.from_user.username}"
    )
    
    # Создаем новую клавиатуру только с кнопкой связи
    contact_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💬 Связаться с пользователем",
            url=f"tg://user?id={user_id}"
        )]
    ])
    
    # Обновляем сообщение
    await callback.message.edit_text(
        new_text,
        reply_markup=contact_kb
    )
    
    # Отправляем уведомление пользователю
    user_notification = (
        "🎉 Ваш вывод подарка принят!\n\n"
        "✨ Пожалуйста, оставьте отзыв о нашей работе:\n"
        f"👉 {Config.OTZIVI_URL}"
    )
    
    try:
        await bot.send_message(user_id, user_notification)
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
    
    await callback.answer("Вывод успешно принят!", show_alert=True)
