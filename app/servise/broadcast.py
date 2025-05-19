import logging
from aiogram import Bot, types, F
import asyncio
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import Config
import app.database.db_queries as qu
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

router = Router()
broadcast_cancelled = False

class ConfigStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_broadcast_photo = State()
    waiting_for_broadcast_button = State()

async def broadcast_message(bot: Bot, message: str, photo: str = None, button_text: str = None, button_url: str = None):
    global broadcast_cancelled
    broadcast_cancelled = False

    users = await qu.get_all_users()
    
    success_count = 0
    failure_count = 0
    bot_info = await bot.get_me()
    cancel_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="cancel_broadcast")]
    ])
    progress_message_id = None
    for i, user in enumerate(users):
        if broadcast_cancelled:
            break
        try:
            keyboard = None
            if button_text and button_url:
                keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text=button_text, url=button_url)]
                ])
            if photo:
                logging.info(f"Отправка фото пользователю {user.user_id}")
                caption = str(message)
                if len(caption) > 1024:
                    caption = caption[:1021] + "..."
                await bot.send_photo(user.user_id, photo, caption=caption, reply_markup=keyboard, parse_mode="HTML")
            else:
                logging.info(f"Отправка сообщения пользователю {user.user_id}")
                await bot.send_message(user.user_id, message, reply_markup=keyboard, parse_mode="HTML")
            success_count += 1
        except TelegramForbiddenError as e:
            logging.warning(f"Не удалось отправить сообщение пользователю {user.user_id}: {e}")
            failure_count += 1
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logging.info("Message is not modified, skipping error.")
            else:
                logging.error(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")
            failure_count += 1
        except Exception as e:
            logging.error(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")
            failure_count += 1
        
        if (i + 1) % 100 == 0:
            try:
                if progress_message_id is None:
                    progress_message = await bot.send_message(
                        Config.ADMIN_IDS[0],
                        f"Рассылка продолжается...\nУспешно: {success_count}\nНе удалось: {failure_count}",
                        reply_markup=cancel_keyboard
                    )
                    progress_message_id = progress_message.message_id
                else:
                    await bot.edit_message_text(
                        chat_id=Config.ADMIN_IDS[0],
                        message_id=progress_message_id,
                        text=f"Рассылка продолжается...\nУспешно: {success_count}\nНе удалось: {failure_count}",
                        reply_markup=cancel_keyboard
                    )
            except TelegramForbiddenError as e:
                logging.warning(f"Не удалось отправить сообщение о прогрессе: {e}")
        
        await asyncio.sleep(0.05)  # Задержка для отправки 50 сообщений в секунду
    
    try:
        if progress_message_id is not None:
            await bot.edit_message_text(
                chat_id=Config.ADMIN_IDS[0],
                message_id=progress_message_id,
                text=f"Рассылка завершена.\nУспешно: {success_count}\nНе удалось: {failure_count}"
            )
        else:
            await bot.send_message(
                Config.ADMIN_IDS[0],
                f"Рассылка завершена.\nУспешно: {success_count}\nНе удалось: {failure_count}"
            )
    except TelegramForbiddenError as e:
        logging.warning(f"Не удалось отправить сообщение о завершении рассылки: {e}")
    
    return success_count, failure_count

async def preview_broadcast(bot: Bot, chat_id: int, message_text: str, photo: str = None, button_text: str = None, button_url: str = None):
    keyboard = None
    if button_text and button_url:
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=button_text, url=button_url)]
        ])
    if photo:
        caption = message_text
        if len(caption) > 1024:
            caption = caption[:1021] + "..."
        await bot.send_photo(chat_id, photo, caption=caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        await bot.send_message(chat_id, message_text, reply_markup=keyboard, parse_mode="HTML")

async def cancel_broadcast():
    global broadcast_cancelled
    broadcast_cancelled = True

@router.callback_query(F.data == "mailing")
async def broadcast_message_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("📢 Пожалуйста, введите текст сообщения для рассылки:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]))
    await state.set_state(ConfigStates.waiting_for_broadcast_message)

@router.message(ConfigStates.waiting_for_broadcast_message)
async def broadcast_message_handler(message: Message, state: FSMContext):
    await state.update_data(broadcast_message=message.html_text)
    await message.answer("📷 Пожалуйста, отправьте фото для рассылки (или напишите 'нет', если фото не требуется):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]))
    await state.set_state(ConfigStates.waiting_for_broadcast_photo)

@router.message(ConfigStates.waiting_for_broadcast_photo)
async def broadcast_photo_handler(message: Message, state: FSMContext):
    if message.text and message.text.lower() == 'нет':
        await state.update_data(broadcast_photo=None)
    else:
        await state.update_data(broadcast_photo=message.photo[-1].file_id if message.photo else None)

    await message.answer("🔗 Пожалуйста, введите текст кнопки и URL в формате 'текст - ссылка' (или напишите 'нет', если кнопка не требуется):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]))
    await state.set_state(ConfigStates.waiting_for_broadcast_button)

@router.message(ConfigStates.waiting_for_broadcast_button)
async def broadcast_button_handler(message: Message, state: FSMContext):
    if message.text and message.text.lower() == 'нет':
        await state.update_data(broadcast_button_text=None, broadcast_button_url=None)
    else:
        try:
            # Разделяем текст и ссылку по знаку "-"
            parts = message.text.split("-", 1)
            if len(parts) != 2:
                raise ValueError("Неправильный формат кнопки")
            
            button_text = parts[0].strip()
            button_url = parts[1].strip()
            
            if not button_text or not button_url:
                raise ValueError("Текст кнопки и ссылка не могут быть пустыми")
                
            await state.update_data(broadcast_button_text=button_text, broadcast_button_url=button_url)
        except ValueError as e:
            await message.answer(f"❌ Ошибка: {str(e)}. Пожалуйста, введите текст кнопки и URL в формате 'текст - ссылка' (или напишите 'нет', если кнопка не требуется).", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
            ]))
            return

    data = await state.get_data()
    broadcast_message_text = data.get("broadcast_message")
    broadcast_photo = data.get("broadcast_photo")
    broadcast_button_text = data.get("broadcast_button_text")
    broadcast_button_url = data.get("broadcast_button_url")

    await preview_broadcast(
        bot=message.bot,
        chat_id=message.chat.id,
        message_text=broadcast_message_text,
        photo=broadcast_photo,
        button_text=broadcast_button_text,
        button_url=broadcast_button_url
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Запустить рассылку", callback_data="start_broadcast")],
        [InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="cancel_broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])
    await message.answer("Предварительный просмотр рассылки завершен. Вы хотите запустить рассылку?", reply_markup=keyboard)

@router.callback_query(F.data == "start_broadcast")
async def start_broadcast_handler(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_message_text = data.get("broadcast_message")
    broadcast_photo = data.get("broadcast_photo")
    broadcast_button_text = data.get("broadcast_button_text")
    broadcast_button_url = data.get("broadcast_button_url")

    await callback_query.message.edit_text("📢 Рассылка запущена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить рассылку", callback_data="cancel_broadcast")]
    ]))
    await broadcast_message(
        bot=callback_query.bot,
        message=broadcast_message_text,
        photo=broadcast_photo,
        button_text=broadcast_button_text,
        button_url=broadcast_button_url
    )
    await state.clear()
    await callback_query.answer()

@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast_handler(callback_query: CallbackQuery, state: FSMContext):
    await cancel_broadcast()
    await callback_query.message.edit_text("❌ Рассылка отменена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ]))
    await state.clear()
    await callback_query.answer()
