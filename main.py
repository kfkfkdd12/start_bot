import logging
import asyncio
from colorama import init, Fore, Style
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config

from app.database.database import create_all_tables

# Инициализация colorama
init()

class ColoredFormatter(logging.Formatter):
    """Форматтер для цветного логирования"""
    def format(self, record):
        if record.levelno == logging.INFO:
            record.msg = f"{Fore.GREEN}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

# Настраиваем логирование
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

# Создаем handler для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter('%(message)s'))
logger.addHandler(console_handler)

# Отключаем логи от aiogram
logging.getLogger('aiogram').setLevel(logging.WARNING)
logging.getLogger('aiogram.event').setLevel(logging.WARNING)

async def notify_admins(bot: Bot):
    """Отправка уведомления админам о запуске бота"""
    message = (
        "🚀 <b>Бот успешно запущен!</b>\n\n"
        "👨‍💻 <b>Разработчик:</b> <code>gidddra</code>\n"
        "✨ <b>Статус:</b> <code>Активен</code>"
    )
    for admin_id in Config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

async def main():
    # Выводим красивый лог запуска
    logger.info(f"\n{Fore.CYAN}{'~' * 50}")
    logger.info(f"🤖 Бот запускается...")
    logger.info(f"{Fore.YELLOW}👨‍💻 Tg Developer: {Fore.MAGENTA}gidddra{Style.RESET_ALL}")
    logger.info(f"{Fore.CYAN}{'~' * 50}\n")

    # Инициализируем бота и диспетчер
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
 
    try:
        # Запускаем бота
        await create_all_tables()
        await notify_admins(bot)  # Отправляем уведомления админам
        await dp.start_polling(bot)
    finally:
        # Останавливаем сервис автопостов при завершении работы
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())