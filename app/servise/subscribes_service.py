from ..bot import r, bot
from aiogram import types, F
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

logger = logging.getLogger('bot')

# Сервис который будет проверять подписки пользователей на нужные нам каналы
class UserSubscribeService:
    def __init__(self):
        self.join_requests = (
            []
        )  # {"user_id": 123456789, "time": time.time(), "channel_id": 12312}

    async def is_user_subscribed(self, user_id: int, channel_id: int) -> bool:
        """
        Асинхронная проверка подписки пользователя на канал.

        :param user_id: ID пользователя Telegram.
        :param channel_id: ID или username канала.
        :return: True, если пользователь подписан или подал заявку, иначе False.
        """
        try:
            member: ChatMember = await bot.get_chat_member(
                chat_id=channel_id, user_id=user_id
            )

            if member.status not in [
                "member",
                "administrator",
                "creator",
                "restricted",
            ]:
                # Проверяем не подавал ли человек заявку на вступление, и удаляем из массива старые данные которые там больше часу
                for join_request in self.join_requests:
                    if (
                        join_request["user_id"] == user_id
                        and join_request["channel_id"] == channel_id
                    ):
                        if join_request["time"] + 3600 > time.time():
                            return True
                        else:
                            self.join_requests.remove(join_request)
                            return True
            else:
                return True
            return False

        except Exception as e:
            # Если канал недоступен или произошла ошибка
            logger.error(f"Ошибка проверки подписки: {e}")
            return True

    @r.chat_join_request()
    async def on_chat_member_update(self, update: ChatJoinRequest):
        user_id = update.from_user.id
        chat_id = update.chat.id

        # Проверяем, была ли подана заявка на вступление в канал
        self.join_requests.append(
            {"user_id": user_id, "time": time.time(), "channel_id": chat_id}
        )
        logger.info(f"Получена заявка на вступление от пользователя {user_id} в канал {chat_id}")


subscribes_service = UserSubscribeService()
