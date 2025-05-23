from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import Config
import logging
import app.database.db_queries as qu
import random
import string
from app.bot import bot
import json

from . import admin_kb as kb

logger = logging.getLogger(__name__)

# Создаем роутер для админ-команд
router = Router()

class PromoCreation(StatesGroup):
    """Состояния для создания промокода"""
    waiting_for_code = State()  # Ожидание ввода кода
    waiting_for_reward = State()  # Ожидание ввода награды
    waiting_for_activations = State()  # Ожидание ввода количества активаций

class ReferralLinkCreation(StatesGroup):
    """Состояния для создания реферальной ссылки"""
    waiting_for_name = State()  # Ожидание ввода названия

class OPChannelCreation(StatesGroup):
    """Состояния для добавления ОП канала"""
    waiting_for_name = State()  # Ожидание ввода названия
    waiting_for_channel_id = State()  # Ожидание ввода ID канала
    waiting_for_url = State()  # Ожидание ввода URL

class TaskChannelCreation(StatesGroup):
    """Состояния для добавления канала заданий"""
    waiting_for_name = State()  # Ожидание ввода названия
    waiting_for_channel_id = State()  # Ожидание ввода ID канала
    waiting_for_url = State()  # Ожидание ввода URL
    waiting_for_limit = State()  # Ожидание ввода лимита
    waiting_for_reward = State()  # Ожидание ввода награды

class ReferralRewardChange(StatesGroup):
    """Состояния для изменения награды за реферала"""
    waiting_for_reward = State()  # Ожидание ввода новой награды

class AdPostCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_content = State()
    waiting_for_buttons = State()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """
    Обработчик команды /admin
    Проверяет, является ли пользователь админом
    """
    # Проверяем, есть ли пользователь в списке админов
    if message.from_user.id not in Config.ADMIN_IDS:
        logger.warning(f"Пользователь {message.from_user.id} попытался получить доступ к админ-панели")
        return
    
    # Отправляем приветственное сообщение с инлайн-клавиатурой
    await message.answer(
        "👨‍💼 Добро пожаловать в админ-панель!\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main
    )
    logger.info(f"Админ {message.from_user.id} вошел в админ-панель")

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показывает статистику бота"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    try:
        # Получаем статистику
        users_stats = await qu.get_users_stats()
        ad_stats = await qu.get_ad_posts_stats()
        promo_stats = await qu.get_promo_stats()
        channels_stats = await qu.get_channels_stats()

        # Формируем сообщение со статистикой
        stats_text = (
            "📊 <b>Статистика бота</b>\n\n"
            
            "👥 <b>Пользователи:</b>\n"
            f"├ Всего: {users_stats['total_users']}\n"
            f"├ Новых за день: {users_stats['new_users']['day']}\n"
            f"├ Новых за неделю: {users_stats['new_users']['week']}\n"
            f"└ Новых за месяц: {users_stats['new_users']['month']}\n\n"
            
            "📢 <b>Рекламные посты:</b>\n"
            f"├ Всего постов: {ad_stats['total_posts']}\n"
            f"└ Показов всего: {ad_stats['shows']['total']}\n\n"
            
            "🎁 <b>Промокоды:</b>\n"
            f"├ Активных: {promo_stats['active_promos']}\n"
            f"├ Активаций всего: {promo_stats['activations']['total']}\n"
            f"├ Активаций за день: {promo_stats['activations']['day']}\n"
            f"├ Активаций за неделю: {promo_stats['activations']['week']}\n"
            f"└ Активаций за месяц: {promo_stats['activations']['month']}\n\n"
            
            "📈 <b>Задания:</b>\n"
            f"├ Выполнено всего: {channels_stats['completed_tasks']['total']}\n"
            f"├ Выполнено за день: {channels_stats['completed_tasks']['today']}\n"
            f"├ Выполнено за неделю: {channels_stats['completed_tasks']['week']}\n"
            f"└ Выполнено за месяц: {channels_stats['completed_tasks']['month']}\n\n"
            
            "🏆 <b>Топ посты по показам:</b>\n"
        )

        # Добавляем топ посты
        for i, post in enumerate(ad_stats['top_posts'], 1):
            stats_text += f"{i}. {post['name']}: {post['shows']} показов\n"

        # Отправляем статистику с кнопкой "Назад"
        await callback.message.edit_text(
            stats_text,
            reply_markup=kb.admin_stats,  # Используем клавиатуру с кнопкой "Назад"
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await callback.answer("❌ Произошла ошибка при получении статистики", show_alert=True)


# Обработчик кнопки "Назад" в админ-панели
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возвращает в главное меню админ-панели"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    await callback.message.edit_text(
        "👨‍💼 Добро пожаловать в админ-панель!\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main
    )

@router.callback_query(F.data == "create_promo")
async def start_promo_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания промокода"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Генерируем случайный код из 8 символов
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    await callback.message.edit_text(
        f"🎁 <b>Создание промокода</b>\n\n"
        f"Предлагаемый код: <code>{code}</code>\n\n"
        "Вы можете использовать его или ввести свой.\n"
        "Отправьте код промокода или нажмите 'Отмена':",
        reply_markup=kb.promo_cancel,
        parse_mode="HTML"
    )
    await state.set_state(PromoCreation.waiting_for_code)
    await state.update_data(suggested_code=code)

@router.callback_query(F.data == "cancel_promo_creation", PromoCreation.waiting_for_code)
async def cancel_promo_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания промокода"""
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 Добро пожаловать в админ-панель!\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main
    )

@router.message(PromoCreation.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка введенного кода промокода"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    code = message.text.strip().upper()
    
    # Проверяем, не существует ли уже такой промокод
    if await qu.check_promo_code_exists(code):
        await message.answer(
            "❌ Такой промокод уже существует!\n"
            "Пожалуйста, введите другой код или нажмите 'Отмена':",
            reply_markup=kb.promo_cancel
        )
        return

    await state.update_data(code=code)
    await message.answer(
        "💰 Введите количество звезд для награды:",
        reply_markup=kb.promo_cancel
    )
    await state.set_state(PromoCreation.waiting_for_reward)

@router.message(PromoCreation.waiting_for_reward)
async def process_promo_reward(message: Message, state: FSMContext):
    """Обработка введенной награды"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        reward = float(message.text.replace(',', '.'))
        if reward <= 0:
            raise ValueError("Награда должна быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число!\n"
            "Например: 10 или 10.5",
            reply_markup=kb.promo_cancel
        )
        return

    await state.update_data(reward=reward)
    await message.answer(
        "🔢 Введите максимальное количество активаций:",
        reply_markup=kb.promo_cancel
    )
    await state.set_state(PromoCreation.waiting_for_activations)

@router.message(PromoCreation.waiting_for_activations)
async def process_promo_activations(message: Message, state: FSMContext):
    """Обработка введенного количества активаций и создание промокода"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        activations = int(message.text)
        if activations <= 0:
            raise ValueError("Количество активаций должно быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное целое число!",
            reply_markup=kb.promo_cancel
        )
        return

    # Получаем все данные о промокоде
    data = await state.get_data()
    code = data['code']
    reward = data['reward']

    # Создаем промокод в базе данных
    success = await qu.create_promo_code(code, reward, activations)
    
    if not success:
        await message.answer(
            "❌ Произошла ошибка при создании промокода.\n"
            "Пожалуйста, попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=kb.promo_cancel
        )
        return

    # Отправляем подтверждение
    await message.answer(
        f"✅ Промокод успешно создан!\n\n"
        f"🎁 Код: <code>{code}</code>\n"
        f"💰 Награда: {reward} ⭐\n"
        f"🔢 Макс. активаций: {activations}",
        reply_markup=kb.admin_main,
        parse_mode="HTML"
    )

    # Очищаем состояние
    await state.clear()

    # Логируем создание промокода
    logger.info(
        f"Создан новый промокод:\n"
        f"- Код: {code}\n"
        f"- Награда: {reward} ⭐\n"
        f"- Макс. активаций: {activations}\n"
        f"- Создал: {message.from_user.id}"
    )

@router.callback_query(F.data == "create_ref_link")
async def start_ref_link_creation(callback: CallbackQuery, state: FSMContext):
    """Начало создания реферальной ссылки"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    await callback.message.edit_text(
        "🔗 <b>Создание реферальной ссылки</b>\n\n"
        "Введите название для реферальной ссылки\n"
        "Например: 'Мой канал' или 'Реклама в чате'\n\n"
        "Отправьте название или нажмите 'Отмена':",
        reply_markup=kb.ref_link_cancel,
        parse_mode="HTML"
    )
    await state.set_state(ReferralLinkCreation.waiting_for_name)

@router.callback_query(F.data == "cancel_ref_link_creation", ReferralLinkCreation.waiting_for_name)
async def cancel_ref_link_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания реферальной ссылки"""
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 Добро пожаловать в админ-панель!\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main
    )

@router.message(ReferralLinkCreation.waiting_for_name)
async def process_ref_link_name(message: Message, state: FSMContext):
    """Обработка введенного названия реферальной ссылки"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    name = message.text.strip()
    if len(name) > 255:
        await message.answer(
            "❌ Название слишком длинное!\n"
            "Максимальная длина - 255 символов.\n"
            "Пожалуйста, введите более короткое название или нажмите 'Отмена':",
            reply_markup=kb.ref_link_cancel
        )
        return

    # Создаем реферальную ссылку
    success, code, error = await qu.create_referral_link(name, message.from_user.id)
    
    if not success:
        await message.answer(
            f"❌ Ошибка при создании реферальной ссылки: {error}\n"
            "Пожалуйста, попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=kb.ref_link_cancel
        )
        return

    # Формируем полную ссылку
    bot_info = await bot.get_me()
    full_link = f"https://t.me/{bot_info.username}?start={code}"

    # Отправляем результат
    await message.answer(
        f"✅ Реферальная ссылка успешно создана!\n\n"
        f"📝 Название: {name}\n"
        f"🔗 Ссылка: <code>{full_link}</code>\n"
        f"🆔 Код: <code>{code}</code>\n\n"
        f"📊 Статистика использования будет доступна в админ-панели",
        reply_markup=kb.admin_main,
        parse_mode="HTML"
    )

    # Очищаем состояние
    await state.clear()

    # Логируем создание ссылки
    logger.info(
        f"Создана новая реферальная ссылка:\n"
        f"- Название: {name}\n"
        f"- Код: {code}\n"
        f"- Создал: {message.from_user.id}"
    )

@router.callback_query(F.data == "show_ref_links")
async def show_ref_links(callback: CallbackQuery):
    """Показывает список реферальных ссылок админа"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем первую страницу ссылок
    links, total_pages = await qu.get_admin_ref_links(callback.from_user.id, page=0)
    
    if not links:
        await callback.message.edit_text(
            "📋 У вас пока нет реферальных ссылок.\n\n"
            "Создайте новую ссылку, нажав на кнопку 'Создать реф. ссылку'",
            reply_markup=kb.admin_main
        )
        return
    
    # Формируем текст сообщения
    text = "📋 <b>Ваши реферальные ссылки:</b>\n\n"
    
    # Отправляем сообщение с первой страницей ссылок
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_ref_links_keyboard(links, page=0, total_pages=total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("ref_links_page_"))
async def handle_ref_links_pagination(callback: CallbackQuery):
    """Обработчик пагинации списка реферальных ссылок"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем номер страницы из callback_data
    page = int(callback.data.split("_")[-1])
    
    # Получаем ссылки для указанной страницы
    links, total_pages = await qu.get_admin_ref_links(callback.from_user.id, page=page)
    
    if not links:
        await callback.answer("Страница не найдена", show_alert=True)
        return
    
    # Обновляем сообщение с новой страницей
    await callback.message.edit_text(
        "📋 <b>Ваши реферальные ссылки:</b>\n\n",
        reply_markup=kb.get_ref_links_keyboard(links, page=page, total_pages=total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("ref_link_"))
async def handle_ref_link_action(callback: CallbackQuery):
    """Обработчик действий с реферальной ссылкой"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем ID ссылки и действие из callback_data
    parts = callback.data.split("_")
    if len(parts) == 3 and parts[2] == "deactivate":
        # Обработка деактивации/активации ссылки
        link_id = int(parts[3])
        success = await qu.toggle_ref_link_status(link_id)
        
        if success:
            # Получаем обновленную информацию о ссылке
            link = await qu.get_ref_link_details(link_id)
            if link:
                status = "деактивирована" if not link['is_active'] else "активирована"
                await callback.answer(f"✅ Ссылка {status}!", show_alert=True)
                
                # Обновляем информацию о ссылке
                await show_ref_link_details(callback, link)
            else:
                await callback.answer("❌ Ссылка не найдена", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при изменении статуса ссылки", show_alert=True)
    else:
        # Просмотр деталей ссылки
        link_id = int(parts[2])
        link = await qu.get_ref_link_details(link_id)
        
        if link:
            await show_ref_link_details(callback, link)
        else:
            await callback.answer("❌ Ссылка не найдена", show_alert=True)

async def show_ref_link_details(callback: CallbackQuery, link: dict):
    """Показывает детальную информацию о реферальной ссылке"""
    # Формируем полную ссылку
    bot_info = await bot.get_me()
    full_link = f"https://t.me/{bot_info.username}?start={link['code']}"
    
    # Форматируем даты
    created_at = link['created_at'].strftime("%d.%m.%Y %H:%M")
    last_used = link['last_used_at'].strftime("%d.%m.%Y %H:%M") if link['last_used_at'] else "Никогда"
    
    # Получаем расширенную статистику
    stats = await qu.get_referral_stats(link['code'])
    
    # Рассчитываем проценты
    op_percentage = (stats['completed_op'] / link['uses_count'] * 100) if link['uses_count'] > 0 else 0
    completed_tasks_percentage = (stats['tasks']['completed'] / stats['tasks']['started'] * 100) if stats['tasks']['started'] > 0 else 0
    
    # Форматируем проценты до 1 знака после запятой
    op_percentage_str = f"{op_percentage:.1f}%"
    completed_tasks_percentage_str = f"{completed_tasks_percentage:.1f}%"
    
    text = (
        f"🔗 <b>Информация о реферальной ссылке</b>\n\n"
        f"📝 Название: {link['name']}\n"
        f"🆔 Код: <code>{link['code']}</code>\n"
        f"🔗 Ссылка: <code>{full_link}</code>\n\n"
        f"📊 Статистика:\n"
        f"├ Использований: {link['uses_count']}\n"
        f"├ Прошли опрос: {stats['completed_op']} ({op_percentage_str})\n"
        f"├ Задания:\n"
        f"│   ├ Начато: {stats['tasks']['started']}\n"
        f"│   ├ Выполнено: {stats['tasks']['completed']} ({completed_tasks_percentage_str})\n"
        f"│   └ В процессе: {stats['tasks']['in_progress']}\n"
        f"├ Последнее использование: {last_used}\n"
        f"├ Создана: {created_at}\n"
        f"└ Статус: {'✅ Активна' if link['is_active'] else '❌ Деактивирована'}\n\n"
        f"👤 Создал: @{link['creator']['username'] if link['creator'] else 'Неизвестно'}"
    )
    
    # Отправляем сообщение с деталями
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_ref_link_details_keyboard(link['id']),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "op_channels")
async def show_op_channels_menu(callback: CallbackQuery):
    """Показывает меню управления ОП каналами"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 <b>Управление ОП каналами</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.op_channels_menu,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "op_channels_list")
async def show_op_channels_list(callback: CallbackQuery):
    """Показывает список ОП каналов"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем список каналов
    channels = await qu.get_all_op_channels()
    
    if not channels:
        await callback.message.edit_text(
            "📢 У вас пока нет ОП каналов.\n\n"
            "Добавьте новый канал, нажав на кнопку 'Добавить'",
            reply_markup=kb.op_channels_menu
        )
        return
    
    # Отправляем список каналов
    await callback.message.edit_text(
        "📢 <b>Список ОП каналов:</b>\n\n"
        "Выберите канал для управления:",
        reply_markup=kb.get_op_channels_keyboard(channels),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "op_channel_add")
async def start_op_channel_creation(callback: CallbackQuery, state: FSMContext):
    """Начало добавления ОП канала"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    await callback.message.edit_text(
        "📢 <b>Добавление ОП канала</b>\n\n"
        "Введите название канала:",
        reply_markup=kb.op_channel_cancel,
        parse_mode="HTML"
    )
    await state.set_state(OPChannelCreation.waiting_for_name)

@router.message(OPChannelCreation.waiting_for_name)
async def process_op_channel_name(message: Message, state: FSMContext):
    """Обработка введенного названия ОП канала"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    name = message.text.strip()
    if len(name) > 255:
        await message.answer(
            "❌ Название слишком длинное!\n"
            "Максимальная длина - 255 символов.\n"
            "Пожалуйста, введите более короткое название или нажмите 'Отмена':",
            reply_markup=kb.op_channel_cancel
        )
        return

    await state.update_data(name=name)
    await message.answer(
        "Введите ID канала (например: -1001234567890):",
        reply_markup=kb.op_channel_cancel
    )
    await state.set_state(OPChannelCreation.waiting_for_channel_id)

@router.message(OPChannelCreation.waiting_for_channel_id)
async def process_op_channel_id(message: Message, state: FSMContext):
    """Обработка введенного ID ОП канала"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID канала!\n"
            "ID должен быть числом (например: -1001234567890)",
            reply_markup=kb.op_channel_cancel
        )
        return

    await state.update_data(channel_id=channel_id)
    await message.answer(
        "Введите URL канала (например: https://t.me/channel):",
        reply_markup=kb.op_channel_cancel
    )
    await state.set_state(OPChannelCreation.waiting_for_url)

@router.message(OPChannelCreation.waiting_for_url)
async def process_op_channel_url(message: Message, state: FSMContext):
    """Обработка введенного URL ОП канала и создание канала"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    url = message.text.strip()
    if not url.startswith(("https://t.me/", "https://telegram.me/")):
        await message.answer(
            "❌ Пожалуйста, введите корректный URL канала!\n"
            "URL должен начинаться с https://t.me/ или https://telegram.me/",
            reply_markup=kb.op_channel_cancel
        )
        return

    # Получаем все данные о канале
    data = await state.get_data()
    name = data['name']
    channel_id = data['channel_id']

    # Создаем канал
    success, error = await qu.add_op_channel(name, channel_id, url)
    
    if not success:
        await message.answer(
            f"❌ Ошибка при добавлении канала: {error}\n"
            "Пожалуйста, попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=kb.op_channel_cancel
        )
        return

    # Отправляем подтверждение
    await message.answer(
        f"✅ ОП канал успешно добавлен!\n\n"
        f"📝 Название: {name}\n"
        f"🆔 ID: {channel_id}\n"
        f"🔗 URL: {url}",
        reply_markup=kb.op_channels_menu
    )

    # Очищаем состояние
    await state.clear()

@router.callback_query(F.data.startswith("op_channel_"))
async def handle_op_channel_action(callback: CallbackQuery):
    """Обработчик действий с ОП каналом"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем ID канала и действие из callback_data
    parts = callback.data.split("_")
    if len(parts) == 4 and parts[2] == "delete":
        # Обработка удаления канала
        channel_id = int(parts[3])
        success = await qu.delete_op_channel(channel_id)
        
        if success:
            await callback.answer("✅ Канал успешно удален!", show_alert=True)
            # Обновляем список каналов
            await show_op_channels_list(callback)
        else:
            await callback.answer("❌ Ошибка при удалении канала", show_alert=True)
    elif len(parts) == 4 and parts[2] == "toggle":
        # Обработка изменения статуса канала
        channel_id = int(parts[3])
        success = await qu.toggle_op_channel_status(channel_id)
        
        if success:
            # Получаем обновленную информацию о канале
            channel = await qu.get_op_channel(channel_id)
            if channel:
                status = "активирован" if channel['is_active'] else "деактивирован"
                await callback.answer(f"✅ Канал {status}!", show_alert=True)
                await show_op_channel_details(callback, channel)
            else:
                await callback.answer("❌ Канал не найден", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при изменении статуса канала", show_alert=True)
    else:
        # Просмотр деталей канала
        channel_id = int(parts[2])
        channel = await qu.get_op_channel(channel_id)
        
        if channel:
            await show_op_channel_details(callback, channel)
        else:
            await callback.answer("❌ Канал не найден", show_alert=True)

async def show_op_channel_details(callback: CallbackQuery, channel: dict):
    """Показывает детальную информацию о канале"""
    status = "✅ Активен" if channel['is_active'] else "❌ Неактивен"
    text = (
        f"📢 Канал: {channel['name']}\n"
        f"🆔 ID канала: {channel['channel_id']}\n"
        f"🔗 Ссылка: {channel['url']}\n"
        f"📊 Статус: {status}\n"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_op_channel_details_keyboard(channel['id'])
    )

@router.callback_query(F.data == "task_channels")
async def show_task_channels_menu(callback: CallbackQuery):
    """Показывает меню управления каналами заданий"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    await callback.message.edit_text(
        "📝 <b>Управление каналами заданий</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.task_channels_menu,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "task_channels_list")
async def show_task_channels_list(callback: CallbackQuery):
    """Показывает список каналов заданий"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем список каналов
    channels = await qu.get_all_task_channels()
    
    if not channels:
        await callback.message.edit_text(
            "📝 У вас пока нет каналов заданий.\n\n"
            "Добавьте новый канал, нажав на кнопку 'Добавить'",
            reply_markup=kb.task_channels_menu
        )
        return
    
    # Отправляем список каналов
    await callback.message.edit_text(
        "📝 <b>Список каналов заданий:</b>\n\n"
        "Выберите канал для управления:",
        reply_markup=kb.get_task_channels_keyboard(channels),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "task_channel_add")
async def start_task_channel_creation(callback: CallbackQuery, state: FSMContext):
    """Начало добавления канала заданий"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    await callback.message.edit_text(
        "📝 <b>Добавление канала заданий</b>\n\n"
        "Введите название канала:",
        reply_markup=kb.task_channel_cancel,
        parse_mode="HTML"
    )
    await state.set_state(TaskChannelCreation.waiting_for_name)

@router.message(TaskChannelCreation.waiting_for_name)
async def process_task_channel_name(message: Message, state: FSMContext):
    """Обработка введенного названия канала заданий"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    name = message.text.strip()
    if len(name) > 255:
        await message.answer(
            "❌ Название слишком длинное!\n"
            "Максимальная длина - 255 символов.\n"
            "Пожалуйста, введите более короткое название или нажмите 'Отмена':",
            reply_markup=kb.task_channel_cancel
        )
        return

    await state.update_data(name=name)
    await message.answer(
        "Введите ID канала (например: -1001234567890):",
        reply_markup=kb.task_channel_cancel
    )
    await state.set_state(TaskChannelCreation.waiting_for_channel_id)

@router.message(TaskChannelCreation.waiting_for_channel_id)
async def process_task_channel_id(message: Message, state: FSMContext):
    """Обработка введенного ID канала заданий"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный ID канала!\n"
            "ID должен быть числом (например: -1001234567890)",
            reply_markup=kb.task_channel_cancel
        )
        return

    await state.update_data(channel_id=channel_id)
    await message.answer(
        "Введите URL канала (например: https://t.me/channel):",
        reply_markup=kb.task_channel_cancel
    )
    await state.set_state(TaskChannelCreation.waiting_for_url)

@router.message(TaskChannelCreation.waiting_for_url)
async def process_task_channel_url(message: Message, state: FSMContext):
    """Обработка введенного URL канала заданий"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    url = message.text.strip()
    if not url.startswith(("https://t.me/", "https://telegram.me/")):
        await message.answer(
            "❌ Пожалуйста, введите корректный URL канала!\n"
            "URL должен начинаться с https://t.me/ или https://telegram.me/",
            reply_markup=kb.task_channel_cancel
        )
        return

    await state.update_data(url=url)
    await message.answer(
        "Введите лимит выполнений (например: 100):",
        reply_markup=kb.task_channel_cancel
    )
    await state.set_state(TaskChannelCreation.waiting_for_limit)

@router.message(TaskChannelCreation.waiting_for_limit)
async def process_task_channel_limit(message: Message, state: FSMContext):
    """Обработка введенного лимита канала заданий"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        limit = int(message.text.strip())
        if limit <= 0:
            raise ValueError("Лимит должен быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число!\n"
            "Лимит должен быть положительным целым числом",
            reply_markup=kb.task_channel_cancel
        )
        return

    await state.update_data(limit=limit)
    await message.answer(
        "Введите награду за выполнение (например: 5):",
        reply_markup=kb.task_channel_cancel
    )
    await state.set_state(TaskChannelCreation.waiting_for_reward)

@router.message(TaskChannelCreation.waiting_for_reward)
async def process_task_channel_reward(message: Message, state: FSMContext):
    """Обработка введенной награды и создание канала заданий"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        reward = float(message.text.replace(',', '.'))
        if reward <= 0:
            raise ValueError("Награда должна быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число!\n"
            "Например: 5 или 5.5",
            reply_markup=kb.task_channel_cancel
        )
        return

    # Получаем все данные о канале
    data = await state.get_data()
    name = data['name']
    channel_id = data['channel_id']
    url = data['url']
    limit = data['limit']

    # Создаем канал
    success, error = await qu.add_task_channel(name, channel_id, url, limit, reward)
    
    if not success:
        await message.answer(
            f"❌ Ошибка при добавлении канала: {error}\n"
            "Пожалуйста, попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=kb.task_channel_cancel
        )
        return

    # Отправляем подтверждение
    await message.answer(
        f"✅ Канал заданий успешно добавлен!\n\n"
        f"📝 Название: {name}\n"
        f"🆔 ID: {channel_id}\n"
        f"🔗 URL: {url}\n"
        f"📊 Лимит: {limit}\n"
        f"💰 Награда: {reward} ⭐",
        reply_markup=kb.task_channels_menu
    )

    # Очищаем состояние
    await state.clear()

@router.callback_query(F.data.startswith("task_channel_"))
async def handle_task_channel_action(callback: CallbackQuery):
    """Обработчик действий с каналом заданий"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем ID канала и действие из callback_data
    parts = callback.data.split("_")
    if len(parts) == 4 and parts[2] == "delete":
        # Обработка удаления канала
        channel_id = int(parts[3])
        success = await qu.delete_task_channel(channel_id)
        
        if success:
            await callback.answer("✅ Канал успешно удален!", show_alert=True)
            # Обновляем список каналов
            await show_task_channels_list(callback)
        else:
            await callback.answer("❌ Ошибка при удалении канала", show_alert=True)
    elif len(parts) == 4 and parts[2] == "toggle":
        # Обработка изменения статуса канала
        channel_id = int(parts[3])
        success = await qu.toggle_task_channel_status(channel_id)
        
        if success:
            # Получаем обновленную информацию о канале
            channel = await qu.get_task_channel(channel_id)
            if channel:
                status = "активирован" if channel['is_active'] else "деактивирован"
                await callback.answer(f"✅ Канал {status}!", show_alert=True)
                await show_task_channel_details(callback, channel)
            else:
                await callback.answer("❌ Канал не найден", show_alert=True)
        else:
            await callback.answer("❌ Ошибка при изменении статуса канала", show_alert=True)
    else:
        # Просмотр деталей канала
        channel_id = int(parts[2])
        channel = await qu.get_task_channel(channel_id)
        
        if channel:
            await show_task_channel_details(callback, channel)
        else:
            await callback.answer("❌ Канал не найден", show_alert=True)

async def show_task_channel_details(callback: CallbackQuery, channel: dict):
    """Показывает детальную информацию о канале заданий"""
    status = "✅ Активен" if channel['is_active'] else "❌ Неактивен"
    text = (
        f"📝 Канал: {channel['name']}\n"
        f"🆔 ID канала: {channel['channel_id']}\n"
        f"🔗 Ссылка: {channel['url']}\n"
        f"📊 Статус: {status}\n"
        f"👥 Всего заданий: {channel['total_limit']}\n"
        f"✅ Выполнено: {channel['completed_count']}\n"
        f"📈 Осталось: {channel['current_limit']}\n"
        f"💰 Награда: {channel['reward']} ⭐"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_task_channel_details_keyboard(channel['id'])
    )

@router.callback_query(F.data == "cancel_task_channel_creation", TaskChannelCreation)
async def cancel_task_channel_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания канала заданий"""
    await state.clear()
    await callback.message.edit_text(
        "📝 <b>Управление каналами заданий</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.task_channels_menu,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "change_referral_reward")
async def start_referral_reward_change(callback: CallbackQuery, state: FSMContext):
    """Начало изменения награды за реферала"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Получаем текущую награду
    current_reward = await qu.get_current_referral_reward()

    await callback.message.edit_text(
        f"💰 <b>Изменение награды за реферала</b>\n\n"
        f"Текущая награда: {current_reward} ⭐\n\n"
        "Введите новую награду (например: 5 или 5.5):",
        reply_markup=kb.referral_reward_cancel,
        parse_mode="HTML"
    )
    await state.set_state(ReferralRewardChange.waiting_for_reward)

@router.callback_query(F.data == "cancel_referral_reward_change", ReferralRewardChange.waiting_for_reward)
async def cancel_referral_reward_change(callback: CallbackQuery, state: FSMContext):
    """Отмена изменения награды за реферала"""
    await state.clear()
    await callback.message.edit_text(
        "👨‍💼 Добро пожаловать в админ-панель!\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_main
    )

@router.message(ReferralRewardChange.waiting_for_reward)
async def process_referral_reward(message: Message, state: FSMContext):
    """Обработка введенной новой награды за реферала"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return

    try:
        new_reward = float(message.text.replace(',', '.'))
        if new_reward <= 0:
            raise ValueError("Награда должна быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное число!\n"
            "Например: 5 или 5.5",
            reply_markup=kb.referral_reward_cancel
        )
        return

    # Обновляем награду
    success = await qu.update_referral_reward(new_reward)
    
    if success:
        await message.answer(
            f"✅ Награда за реферала успешно изменена!\n\n"
            f"💰 Новая награда: {new_reward} ⭐",
            reply_markup=kb.admin_main
        )
        logger.info(f"Изменена награда за реферала: {new_reward} ⭐ (изменил: {message.from_user.id})")
    else:
        await message.answer(
            "❌ Произошла ошибка при изменении награды.\n"
            "Пожалуйста, попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=kb.referral_reward_cancel
        )

    await state.clear()

@router.callback_query(F.data == "ad_posts")
async def show_ad_posts_menu(callback: CallbackQuery):
    """Показывает меню управления рекламными постами"""
    await callback.message.edit_text(
        "📢 Управление рекламными постами\n\n"
        "Здесь вы можете управлять рекламными постами, которые будут показываться пользователям.",
        reply_markup=kb.ad_posts_menu
    )

@router.callback_query(F.data == "ad_posts_list")
async def show_ad_posts_list(callback: CallbackQuery):
    """Показывает список рекламных постов"""
    posts = await qu.get_all_ad_posts()
    if not posts:
        await callback.message.edit_text(
            "📢 Список рекламных постов пуст\n\n"
            "Добавьте новый пост, нажав кнопку «➕ Добавить»",
            reply_markup=kb.ad_posts_menu
        )
        return
        
    await callback.message.edit_text(
        "📢 Список рекламных постов:\n\n"
        "Выберите пост для управления:",
        reply_markup=kb.get_ad_posts_keyboard(posts)
    )

@router.callback_query(F.data == "ad_post_add")
async def start_ad_post_creation(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс создания рекламного поста"""
    await callback.message.edit_text(
        "📝 Создание рекламного поста\n\n"
        "Введите название поста:",
        reply_markup=kb.ad_post_cancel
    )
    await state.set_state(AdPostCreation.waiting_for_name)

@router.callback_query(F.data == "cancel_ad_post_creation")
async def cancel_ad_post_creation(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание рекламного поста"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание поста отменено",
        reply_markup=kb.ad_posts_menu
    )

@router.message(AdPostCreation.waiting_for_name)
async def process_ad_post_name(message: Message, state: FSMContext):
    """Обрабатывает название рекламного поста"""
    await state.update_data(name=message.text)
    await message.answer(
        "📝 Введите текст поста с HTML-разметкой:\n\n"
        "Поддерживаемые теги:\n"
        "- <b>жирный текст</b>\n"
        "- <i>курсив</i>\n"
        "- <u>подчеркнутый</u>\n"
        "- <code>моноширинный</code>\n"
        "- <a href='ссылка'>текст ссылки</a>",
        reply_markup=kb.ad_post_cancel
    )
    await state.set_state(AdPostCreation.waiting_for_content)

@router.message(AdPostCreation.waiting_for_content)
async def process_ad_post_content(message: Message, state: FSMContext):
    """Обрабатывает контент рекламного поста"""
    # Сохраняем текст с HTML-разметкой из сообщения
    await state.update_data(text=message.html_text)
    
    await message.answer(
        "🔗 Добавьте кнопки (необязательно):\n\n"
        "Введите кнопки в формате:\n"
        "текст кнопки - ссылка, текст кнопки - ссылка\n\n"
        "Например:\n"
        "Наш канал - https://t.me/channel, Сайт - https://site.com\n\n"
        "Или отправьте «нет» если кнопки не нужны",
        reply_markup=kb.ad_post_cancel
    )
    await state.set_state(AdPostCreation.waiting_for_buttons)

@router.message(AdPostCreation.waiting_for_buttons)
async def process_ad_post_buttons(message: Message, state: FSMContext):
    """Обрабатывает кнопки рекламного поста"""
    data = await state.get_data()
    buttons = None
    
    if message.text.lower() != "нет":
        try:
            # Проверяем формат кнопок
            button_pairs = [pair.strip() for pair in message.text.split(",")]
            for pair in button_pairs:
                if " - " not in pair:
                    raise ValueError("Неверный формат кнопки")
            
            # Сохраняем кнопки в исходном формате
            buttons = message.text.strip()
            
        except Exception as e:
            await message.answer(
                "❌ Ошибка в формате кнопок!\n\n"
                "Пожалуйста, используйте формат:\n"
                "текст кнопки - ссылка, текст кнопки - ссылка",
                reply_markup=kb.ad_post_cancel
            )
            return
    
    # Добавляем пост в базу
    success, error = await qu.add_ad_post(
        name=data['name'],
        text=data['text'],
        url=buttons  # Сохраняем кнопки в исходном формате
    )
    
    if success:
        await message.answer(
            "✅ Рекламный пост успешно создан!",
            reply_markup=kb.ad_posts_menu
        )
    else:
        await message.answer(
            f"❌ Ошибка при создании поста: {error}",
            reply_markup=kb.ad_posts_menu
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("ad_post_"))
async def handle_ad_post_action(callback: CallbackQuery):
    """Обработчик действий с рекламным постом"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    # Parse the callback data
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ Неверный формат данных", show_alert=True)
        return

    action = parts[2] if len(parts) > 3 else "view"
    post_id = int(parts[-1])

    if action == "delete":
        # Сначала проверяем существование поста
        post = await qu.get_ad_post(post_id)
        if not post:
            await callback.answer("❌ Пост не найден", show_alert=True)
            return
            
        # Запрашиваем подтверждение удаления
        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите удалить пост «{post['name']}»?\n\n"
            "Это действие нельзя отменить!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"_delete_{post_id}"),
                    InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"ad_post_{post_id}")
                ]
            ])
        )
    else:
        # Получаем информацию о посте
        post = await qu.get_ad_post(post_id)
        if post:
            await show_ad_post_details(callback, post)
        else:
            await callback.answer("❌ Пост не найден", show_alert=True)

@router.callback_query(F.data.startswith("_delete_"))
async def confirm_delete_ad_post(callback: CallbackQuery):
    """Подтверждение удаления рекламного поста"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("⛔️ У вас нет доступа к этой функции", show_alert=True)
        return

    try:
        post_id = int(callback.data.split("_")[-1])
        
        # Удаляем пост
        success = await qu.delete_ad_post(post_id)
        
        if success:
            await callback.answer("✅ Пост успешно удален", show_alert=True)
            # Удаляем сообщение с деталями поста            # Возвращаемся к списку постов
            await show_ad_posts_list(callback)
        else:
            await callback.answer("❌ Ошибка при удалении поста", show_alert=True)
            # Возвращаемся к списку постов в любом случае
            await show_ad_posts_list(callback)
            
    except Exception as e:
        logger.error(f"Ошибка при удалении поста: {e}")
        await callback.answer("❌ Произошла ошибка при удалении поста", show_alert=True)
        # Возвращаемся к списку постов даже в случае ошибки
        await show_ad_posts_list(callback)

async def show_ad_post_details(callback: CallbackQuery, post: dict):
    """Показывает детали рекламного поста"""
    text = (
        f"📝 <b>Рекламный пост</b>\n\n"
        f"📌 Название: {post['name']}\n"
        f"👁 Показов: {post['show_count']}\n"
    )
    
    # Добавляем дату создания только если она есть
    if post['created_at']:
        text += f"📅 Создан: {post['created_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    text += f"📄 Текст:\n{post['text']}\n"
    
    # Добавляем кнопки, если они есть
    if post['url']:
        text += f"\n🔗 Кнопки:\n{post['url']}"
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_ad_post_details_keyboard(post['id']),
        parse_mode="HTML"
    )
