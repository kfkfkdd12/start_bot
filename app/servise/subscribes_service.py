from ..bot import  bot
from aiogram import types, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMemberUpdated,
    ChatMember,
    ChatJoinRequest,
)
import time
import asyncio
import logging
import signal
from ..database import db_queries as qu
from collections import defaultdict

logger = logging.getLogger('bot')

r = Router()

# Сервис который будет проверять подписки пользователей на нужные нам каналы
class UserSubscribeService:
    def __init__(self):
        # Используем defaultdict для эффективного хранения заявок
        # Структура: {channel_id: {user_id: timestamp}}
        self._join_requests = defaultdict(dict)
        self.CLEANUP_INTERVAL = 60  # Проверка каждые 60 секунд
        self.REQUEST_TIMEOUT = 300  # 5 минут в секундах
        self._cleanup_task = None
        self._lock = asyncio.Lock()  # Для безопасного доступа к данным
        self._is_running = False

    async def start(self):
        """Запускает фоновую задачу очистки заявок"""
        if self._cleanup_task is None and not self._is_running:
            self._is_running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_old_requests())
            logger.info("Задача очистки заявок запущена")

    async def stop(self):
        """Корректно останавливает сервис"""
        if self._is_running:
            self._is_running = False
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            self._cleanup_task = None
            # Очищаем все заявки при остановке
            async with self._lock:
                self._join_requests.clear()
            logger.info("Сервис подписок остановлен")

    async def _cleanup_old_requests(self):
        """Периодически очищает устаревшие заявки"""
        while self._is_running:
            try:
                async with self._lock:
                    current_time = time.time()
                    # Очищаем устаревшие заявки для каждого канала
                    for channel_id in list(self._join_requests.keys()):
                        # Очищаем устаревшие заявки для канала
                        self._join_requests[channel_id] = {
                            user_id: timestamp
                            for user_id, timestamp in self._join_requests[channel_id].items()
                            if current_time - timestamp < self.REQUEST_TIMEOUT
                        }
                        # Удаляем пустой канал
                        if not self._join_requests[channel_id]:
                            del self._join_requests[channel_id]
                    
                    total_requests = sum(len(requests) for requests in self._join_requests.values())
                    logger.info(f"Очистка заявок выполнена. Осталось заявок: {total_requests}")
            except asyncio.CancelledError:
                logger.info("Задача очистки заявок остановлена")
                break
            except Exception as e:
                logger.error(f"Ошибка при очистке заявок: {e}")
            
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
            except asyncio.CancelledError:
                break

    async def is_user_subscribed(self, user_id: int, channel_id: int, is_join_request: bool = False) -> bool:
        """
        Асинхронная проверка подписки пользователя на канал.

        :param user_id: ID пользователя Telegram.
        :param channel_id: ID или username канала.
        :param is_join_request: True если канал настроен на заявки, False если на подписки.
        :return: True, если пользователь подписан или подал заявку, иначе False.
        """
        try:
            # Пропускаем проверку для канала с ID 0
            if channel_id == 0:
                return True

            # Для каналов на заявки проверяем только наличие заявки в кэше
            if is_join_request:
                async with self._lock:
                    if channel_id in self._join_requests and user_id in self._join_requests[channel_id]:
                        timestamp = self._join_requests[channel_id][user_id]
                        if time.time() - timestamp < self.REQUEST_TIMEOUT:
                            return True
                        else:
                            # Удаляем устаревшую заявку
                            del self._join_requests[channel_id][user_id]
                            # Удаляем пустой канал
                            if not self._join_requests[channel_id]:
                                del self._join_requests[channel_id]
                return False

            # Для обычных каналов проверяем подписку
            try:
                member: ChatMember = await bot.get_chat_member(
                    chat_id=channel_id, user_id=user_id
                )
                return member.status in ["member", "administrator", "creator", "restricted"]
            except Exception as e:
                logger.error(f"Ошибка проверки подписки на канал {channel_id}: {e}")
                return False

        except Exception as e:
            logger.error(f"Критическая ошибка в is_user_subscribed для канала {channel_id}: {e}")
            return False

    @r.chat_join_request()
    async def on_chat_member_update(self, update: ChatJoinRequest):
        """Обработчик новых заявок на вступление"""
        try:
            user_id = update.from_user.id
            chat_id = update.chat.id

            async with self._lock:
                self._join_requests[chat_id][user_id] = time.time()
                logger.info(f"Добавлена заявка на вступление: канал {chat_id}, пользователь {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при обработке заявки на вступление: {e}")

# Создаем экземпляр сервиса
subscribes_service = UserSubscribeService()

# Регистрируем обработчики сигналов для корректного завершения
def handle_exit(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(subscribes_service.stop())
        # Даем время на корректное завершение
        loop.call_later(2, loop.stop)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
