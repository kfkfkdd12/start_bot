import logging
import asyncio
from colorama import init, Fore, Style
from aiogram.enums import ParseMode

from config import Config
from app.database.database import create_all_tables
from app.servise import subscribes_service
from app.bot import bot, dp  # Импортируем только бота и диспетчер, роутер уже подключен
from app.user.handlers import r as user_r
from app.servise.task_handlers import router as task_r
from app.admin.handlers import router as admin_router  # Добавляем импорт админ-роутера
from app.servise.broadcast import router as broadcast_router
from app.servise.subscribes_service import r as subscribes_r
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

async def notify_admins():
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

    try:
        # Запускаем сервис подписок
        await subscribes_service.start()
        logger.info("Сервис подписок запущен")

        #подключаем роутеры
        dp.include_router(user_r)
        dp.include_router(task_r)
        dp.include_router(admin_router)  # Подключаем админ-роутер
        dp.include_router(broadcast_router)
        dp.include_router(subscribes_r)
        # Проверяем подключение бота
        bot_info = await bot.get_me()
        logger.info(f"Бот успешно подключен: @{bot_info.username}")

        # Регистрируем обработчики сервиса подписок
        dp.chat_join_request.register(subscribes_service.on_chat_member_update)
        logger.info("Обработчик заявок на вступление зарегистрирован")
        
        # Создаем таблицы
        await create_all_tables()
        logger.info("База данных инициализирована")
        
        # Отправляем уведомления админам
        await notify_admins()
        logger.info("Уведомления админам отправлены")
        
        # Запускаем бота
        logger.info("Запускаем поллинг...")
        await dp.start_polling(bot)
        logger.info("Бот запущен")

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise
    finally:
        # Останавливаем сервис автопостов при завершении работы
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")