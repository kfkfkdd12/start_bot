from aiogram import types, Router, Bot, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.db_queries import (
    get_next_task, mark_task_completed, decrease_channel_limit, add_reward_to_user,
    get_user_task, add_user_task, get_channel_by_task_id
)
from aiogram.exceptions import TelegramBadRequest
from cachetools import TTLCache

router = Router()

# Кэш для хранения заявок на вступление с TTL 5 минут
join_requests_cache = TTLCache(maxsize=1000, ttl=300)

@router.chat_join_request()
async def handle_join_request(event: types.ChatJoinRequest, bot: Bot):
    """Сохраняем заявки на вступление в кэш."""
    channel_id = event.chat.id
    user_id = event.from_user.id
    join_requests_cache.setdefault(channel_id, set()).add(user_id)

@router.message(F.text == "📚 Задания")
async def give_task(mes: types.Message):
    """Отправляем пользователю следующее задание."""
    user_id = mes.from_user.id
    next_task = await get_next_task(user_id)
    if not next_task:
        await mes.answer("🎉 Все задания выполнены! Возвращайтесь позже.", show_alert=True)
        return

    # Проверяем, есть ли задание в таблице user_tasks
    user_task = await get_user_task(user_id, next_task.id)
    if not user_task:
        await add_user_task(user_id, next_task.id)

     # Определяем текст задания в зависимости от типа канала
    action_text = "Подписаться" if next_task.sab else "Подать заявку"
    task_text = (
            f"📌 <b>Задание:</b> {action_text} в канал <b>{next_task.chanel_name}</b>\n"
            f"💰 <b>Награда:</b> {next_task.reward} ⭐️\n\n"
            "👉 Нажмите кнопку ниже, чтобы выполнить задание."
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнить", url=next_task.link)],
            [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"check_task:{next_task.id}")]
        ])
    await mes.answer(task_text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("check_task:"))
async def check_subscription(callback_query: types.CallbackQuery, bot: Bot):
    """Проверяем выполнение задания."""
    task_id = int(callback_query.data.split(":")[1])
    user_id = callback_query.from_user.id
    try:
        chanel = await get_channel_by_task_id(task_id)
        if not chanel:
            await callback_query.answer("❌ Канал не найден. Обратитесь к администратору.", show_alert=True)
            return

        if chanel.sab:  # Проверяем подписку
            await handle_subscription_check(bot, callback_query, chanel, user_id, task_id)
        else:  # Проверяем заявку на вступление
            await handle_join_request_check(bot, callback_query, chanel, user_id, task_id)

        # Проверяем следующее задание
        next_task = await get_next_task(user_id)
        if next_task:
            # Проверяем, есть ли запись о следующем задании в таблице user_tasks
            user_task = await get_user_task(user_id, next_task.id)
            if not user_task:
                await add_user_task(user_id, next_task.id)

                # Определяем текст задания в зависимости от типа канала
                action_text = "Подписаться" if next_task.sab else "Подать заявку"
                task_text = (
                    f"📌 <b>Следующее задание:</b> {action_text} в канал <b>{next_task.chanel_name}</b>\n"
                    f"💰 <b>Награда:</b> {next_task.reward} 💎\n\n"
                    "👉 Нажмите кнопку ниже, чтобы выполнить задание."
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Выполнить", url=next_task.link)],
                    [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"check_task:{next_task.id}")]
                                                    ])
                await callback_query.message.edit_text(task_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback_query.message.edit_text(
                "🎉 Все задания на сегодня выполнены. Возвращайтесь завтра!",
                parse_mode="HTML"
            )

    except TelegramBadRequest as e:
        error_message = "❌ Произошла ошибка, обратитесь в поддержку."
        if "chat not found" in str(e):
            error_message += " Код ошибки: 1(канал не найден)"
        else:
            error_message += " Код ошибки: 2"
        await callback_query.answer(error_message, show_alert=True)

async def handle_subscription_check(bot: Bot, callback_query: types.CallbackQuery, chanel, user_id: int, task_id: int):
    """Обрабатываем проверку подписки на канал."""
    member = await bot.get_chat_member(chat_id=chanel.chanel_id, user_id=user_id)
    if member.status in ["member", "administrator", "creator"]:
        await mark_task_completed(user_id, task_id)
        await decrease_channel_limit(chanel.id)
        await add_reward_to_user(user_id, chanel.reward)
        await callback_query.answer("🎉 Вы подписаны на канал! Награда начислена. Следующее задание уже у вас", show_alert=True)
    else:
        await callback_query.answer("❌ Вы не подписаны на канал. Пожалуйста, подпишитесь.", show_alert=True)


async def handle_join_request_check(bot: Bot, callback_query: types.CallbackQuery, chanel, user_id: int, task_id: int):
    """Обрабатываем проверку заявки на вступление в канал."""
    member = await bot.get_chat_member(chat_id=chanel.chanel_id, user_id=user_id)
    if member.status in ["member"]:
        await callback_query.answer("❌ Вы подписаны на канал. Отпишитесь и подайте заявку заново.", show_alert=True)
    elif member.status in [ "administrator", "creator"]:
        await mark_task_completed(user_id, task_id)
        await decrease_channel_limit(chanel.id)
        await add_reward_to_user(user_id, chanel.reward)
        await callback_query.answer("🎉 Ваша заявка на вступление подтверждена! Награда начислена. Следующее задание уже у вас", show_alert=True)
    elif chanel.chanel_id in join_requests_cache and user_id in join_requests_cache[chanel.chanel_id]:
        await mark_task_completed(user_id, task_id)
        await decrease_channel_limit(chanel.id)
        await add_reward_to_user(user_id, chanel.reward)
        await callback_query.answer("🎉 Ваша заявка на вступление подтверждена! Награда начислена. Следующее задание уже у вас", show_alert=True)
    else:
        await callback_query.answer("❌ Заявка не найдена. Пожалуйста, подайте заявку заново.", show_alert=True)
