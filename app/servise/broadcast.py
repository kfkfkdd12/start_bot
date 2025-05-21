import logging
from aiogram import Bot, types, F
import asyncio
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import Config
import app.database.db_queries as qu
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)

# Клавиатуры для рассылки
def get_cancel_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_broadcast_preview")]
    ])

def get_confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_broadcast"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_broadcast_preview")
        ]
    ])

def get_cancel_broadcast_progress_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены рассылки во время процесса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Остановить рассылку", callback_data="cancel_broadcast_progress")]
    ])

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

# Глобальные переменные для отслеживания рассылки
broadcast_in_progress = False
broadcast_cancelled = False
broadcast_stats = {
    'total': 0,
    'success': 0,
    'failed': 0,
    'start_time': None,
    'end_time': None
}
broadcast_message = None  # Сохраняем сообщение для рассылки

@router.callback_query(F.data == "broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало процесса рассылки"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этого действия", show_alert=True)
        return
    
    if broadcast_in_progress:
        await callback.answer("❌ Рассылка уже в процессе", show_alert=True)
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await callback.message.edit_text(
        "📢 <b>Отправьте сообщение для рассылки</b>\n\n"
        "Вы можете отправить:\n"
        "• Текст с форматированием\n"
        "• Фото с текстом\n"
        "• Кнопки\n\n"
        "Сообщение будет отправлено всем пользователям бота.",
        reply_markup=get_cancel_broadcast_keyboard(),
        parse_mode="HTML"
    )

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка сообщения для рассылки"""
    global broadcast_message
    
    if message.from_user.id not in Config.ADMIN_IDS:
        return
    
    # Сохраняем сообщение для рассылки
    broadcast_message = message
    
    # Сначала отправляем само сообщение для рассылки
    if message.photo:
        await message.answer_photo(
            message.photo[-1].file_id,
            caption=message.html_text if message.caption_entities else message.caption,
            reply_markup=message.reply_markup,
            parse_mode="HTML" if message.caption_entities else None
        )
    else:
        await message.answer(
            message.html_text if message.entities else message.text,
            reply_markup=message.reply_markup,
            parse_mode="HTML" if message.entities else None
        )
    
    # Затем отправляем предпросмотр сообщения
    preview_text = "📢 <b>Предпросмотр сообщения для рассылки</b>\n\n"
    preview_text += "Сообщение будет отправлено всем пользователям бота.\n"
    preview_text += "Подтвердите или отмените рассылку:"
    
    await message.answer(
        preview_text,
        reply_markup=get_confirm_broadcast_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение рассылки"""
    global broadcast_in_progress, broadcast_cancelled, broadcast_stats, broadcast_message
    
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этого действия", show_alert=True)
        return
    
    if not broadcast_message:
        await callback.answer("❌ Сообщение для рассылки не найдено", show_alert=True)
        return
    
    # Получаем всех пользователей
    users = await qu.get_all_users()
    total_users = len(users)
    
    if total_users == 0:
        await callback.message.answer("❌ Нет пользователей для рассылки")
        await state.clear()
        return
    
    # Инициализируем статистику
    broadcast_stats = {
        'total': total_users,
        'success': 0,
        'failed': 0,
        'start_time': datetime.now(),
        'end_time': None
    }
    
    broadcast_in_progress = True
    broadcast_cancelled = False
    
    # Создаем сообщение со статистикой
    stats_message = await callback.message.answer(
        f"📊 <b>Начало рассылки</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"⏳ Прогресс: {get_progress_bar(0, total_users)}\n"
        f"✅ Успешно: 0\n"
        f"❌ Ошибок: 0\n"
        f"⏱ Время: 0 сек",
        reply_markup=get_cancel_broadcast_progress_keyboard(),
        parse_mode="HTML"
    )
    
    # Отправляем сообщение всем пользователям
    for i, user in enumerate(users, 1):
        if broadcast_cancelled:
            break
            
        try:
            # Копируем сообщение с сохранением форматирования
            if broadcast_message.photo:
                await bot.send_photo(
                    user.user_id,
                    broadcast_message.photo[-1].file_id,
                    caption=broadcast_message.html_text if broadcast_message.caption_entities else broadcast_message.caption,
                    parse_mode="HTML" if broadcast_message.caption_entities else None,
                    reply_markup=broadcast_message.reply_markup
                )
            else:
                # Проверяем наличие форматирования в тексте
                parse_mode = "HTML" if broadcast_message.entities else None
                await bot.send_message(
                    user.user_id,
                    broadcast_message.html_text if broadcast_message.entities else broadcast_message.text,
                    parse_mode=parse_mode,
                    reply_markup=broadcast_message.reply_markup
                )
            broadcast_stats['success'] += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user.user_id}: {e}")
            broadcast_stats['failed'] += 1
        
        # Обновляем статистику каждые 10 сообщений или в конце
        if i % 10 == 0 or i == total_users:
            elapsed_time = (datetime.now() - broadcast_stats['start_time']).total_seconds()
            await stats_message.edit_text(
                f"📊 <b>Рассылка в процессе</b>\n\n"
                f"👥 Всего пользователей: {total_users}\n"
                f"⏳ Прогресс: {get_progress_bar(i, total_users)}\n"
                f"✅ Успешно: {broadcast_stats['success']}\n"
                f"❌ Ошибок: {broadcast_stats['failed']}\n"
                f"⏱ Время: {int(elapsed_time)} сек",
                reply_markup=get_cancel_broadcast_progress_keyboard(),
                parse_mode="HTML"
            )
        
        # Небольшая задержка между сообщениями
        await asyncio.sleep(0.1)
    
    # Завершаем рассылку
    broadcast_in_progress = False
    broadcast_stats['end_time'] = datetime.now()
    total_time = (broadcast_stats['end_time'] - broadcast_stats['start_time']).total_seconds()
    
    if broadcast_cancelled:
        final_message = "❌ Рассылка отменена"
    else:
        final_message = "✅ Рассылка завершена"
    
    await stats_message.edit_text(
        f"{final_message}\n\n"
        f"📊 <b>Итоговая статистика</b>\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Успешно: {broadcast_stats['success']}\n"
        f"❌ Ошибок: {broadcast_stats['failed']}\n"
        f"⏱ Общее время: {int(total_time)} сек\n"
        f"📈 Процент доставки: {broadcast_stats['success'] / total_users * 100:.1f}%",
        reply_markup=None,
        parse_mode="HTML"
    )
    
    await state.clear()
    broadcast_message = None

@router.callback_query(F.data == "cancel_broadcast_preview")
async def cancel_broadcast_preview(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки на этапе предпросмотра"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет прав для выполнения этого действия", show_alert=True)
        return
    
    await callback.message.edit_text(
        "❌ Рассылка отменена",
        reply_markup=None
    )
    await state.clear()
    broadcast_message = None

def get_progress_bar(current: int, total: int, width: int = 20) -> str:
    """
    Создает визуальный индикатор прогресса.
    
    Args:
        current (int): Текущее значение
        total (int): Общее значение
        width (int): Ширина индикатора
        
    Returns:
        str: Строка с индикатором прогресса
    """
    progress = int(width * current / total)
    bar = "█" * progress + "░" * (width - progress)
    percentage = current / total * 100
    return f"{bar} {percentage:.1f}%" 