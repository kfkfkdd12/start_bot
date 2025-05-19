from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import Config

# Инициализация роутера
r = Router()

# Инициализация бота
bot = Bot(
    token=Config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Инициализация диспетчера
dp = Dispatcher()

# Подключаем роутер к диспетчеру
dp.include_router(r)

# Экспортируем все необходимые компоненты
__all__ = ['bot', 'dp', 'r'] 