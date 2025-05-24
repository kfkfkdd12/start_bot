from sqlalchemy.future import select
from sqlalchemy import update, func, insert, delete
from datetime import datetime, timedelta
from . import database as db
from .database import AsyncSessionFactory
from sqlalchemy.exc import OperationalError
from typing import Optional, List, Dict, Any
from config import Config
import random
import string
from sqlalchemy import and_
import logging
from sqlalchemy import case

logger = logging.getLogger(__name__)

async def register_user(user_id: int, username: str, referred_by: str):
    """
    Регистрирует нового пользователя в базе данных.
    Если пользователь пришел по реферальной ссылке, начисляет 3 звезды пригласившему.
    
    Args:
        user_id (int): ID пользователя в Telegram
        username (str): Username пользователя
        referred_by (str): Реферальный код
        
    Returns:
        bool: True если пользователь успешно зарегистрирован, False если пользователь уже существует
    """
    async with AsyncSessionFactory() as session:
        # Проверяем, существует ли пользователь
        stmt = select(db.User).where(db.User.user_id == user_id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            return False
            
        # Если есть реферальный код, ищем пригласившего для начисления звезд
        referrer = None
        if referred_by:
            try:
                # Ищем пользователя с таким реферальным кодом
                stmt = select(db.User).where(db.User.user_id == referred_by)
                result = await session.execute(stmt)
                referrer = result.scalar_one_or_none()
                
                if referrer:
                    try:
                        result = await session.execute(select(db.Settings).order_by(db.Settings.id.desc()).limit(1))
                        settings = result.scalar_one_or_none()
                        reward = settings.referral_reward if settings else 3.0
                        # Начисляем звезды пригласившему
                        stmt = update(db.User).where(
                            db.User.id == referrer.id
                        ).values(
                            balans=db.User.balans + reward
                        )
                        await session.execute(stmt)
                        logger.info(f"Начислено {reward} ⭐ пользователю {referrer.user_id} за приглашение {user_id}")
                    except Exception as e:
                        logger.error(
                            f"Ошибка при начислении звезд рефералу:\n"
                            f"- Реферал: {referrer.user_id} (ID: {referrer.id})\n"
                            f"- Новый пользователь: {user_id}\n"
                            f"- Ошибка: {str(e)}"
                        )
            except Exception as e:
                logger.error(
                    f"Ошибка при поиске реферала:\n"
                    f"- Реферальный код: {referred_by}\n"
                    f"- Новый пользователь: {user_id}\n"
                    f"- Ошибка: {str(e)}"
                )
        
        # Создаем нового пользователя
        new_user = db.User(
            user_id=user_id, 
            username=username,
            referred_by=referred_by,  # Сохраняем реферальный код в любом случае
            created_at=datetime.now()
        )
        session.add(new_user)
        await session.commit()
        
        # Если регистрация прошла успешно и есть реферальный код, пытаемся обновить счетчик
        if referred_by:
            try:
                # Обновляем счетчик использования реферальной ссылки
                stmt = update(db.ReferralLink).where(
                    db.ReferralLink.code == referred_by
                ).values(
                    uses_count=db.ReferralLink.uses_count + 1,
                    last_used_at=datetime.now()
                )
                await session.execute(stmt)
                await session.commit()
                logger.info(f"Увеличен счетчик использования реферальной ссылки {referred_by}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении счетчика реферальной ссылки: {e}")
        
        return True

async def get_all_users():
    """
    Получает список всех пользователей из базы данных.
    
    Returns:
        List[User]: Список всех пользователей
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            stmt = select(db.User)
            result = await session.execute(stmt)
            return result.scalars().all()


async def get_user(user_id: int):
    """
    Получает пользователя по его ID.
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        User: Пользователь
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            stmt = select(db.User).filter(db.User.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalars().first()


async def get_invite_count(user_id: int) -> int:
    """Получает количество приглашенных пользователей (рефералов)
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        int: Количество приглашенных пользователей
    """
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(func.count()).select_from(db.User).filter(db.User.referred_by == int(user_id))
        )
        return result.scalar_one() or 0

async def get_promo_code(code: str):
    """Получить промокод по коду"""
    async with AsyncSessionFactory() as session:
        stmt = select(db.PromoCode).where(
            db.PromoCode.code == code,
            db.PromoCode.is_active == True
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def check_promo_activation(user_id: int, promo_code_id: int):
    """Проверить, активировал ли пользователь промокод"""
    async with AsyncSessionFactory() as session:
        stmt = select(db.PromoCodeActivation).where(
            db.PromoCodeActivation.user_id == user_id,
            db.PromoCodeActivation.promo_code_id == promo_code_id
        )
        result = await session.execute(stmt)
        return result.first() is not None

async def activate_promo_code(user_id: int, promo_code: db.PromoCode):
    """Активировать промокод для пользователя"""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # Получаем пользователя по Telegram ID
            user = await get_user(user_id)
            if not user:
                logger.warning(f"Пользователь с Telegram ID {user_id} не найден")
                return False
                
            # Проверяем, не активировал ли пользователь этот промокод ранее
            if await check_promo_activation(user.id, promo_code.id):
                logger.info(f"Пользователь {user_id} уже активировал промокод {promo_code.code}")
                return False
            
            # Проверяем, не превышен ли лимит активаций
            if promo_code.current_activations >= promo_code.max_activations:
                logger.warning(f"Промокод {promo_code.code} достиг лимита активаций ({promo_code.current_activations}/{promo_code.max_activations})")
                return False
            
            old_balance = user.balans
            old_activations = promo_code.current_activations
            
            # Создаем запись об активации используя внутренний ID пользователя
            activation = db.PromoCodeActivation(
                user_id=user.id,
                promo_code_id=promo_code.id
            )
            session.add(activation)
            
            # Обновляем счетчик активаций промокода
            stmt = update(db.PromoCode).where(
                db.PromoCode.id == promo_code.id
            ).values(
                current_activations=db.PromoCode.current_activations + 1
            )
            await session.execute(stmt)
            
            # Обновляем баланс пользователя
            stmt = update(db.User).where(
                db.User.id == user.id
            ).values(
                balans=db.User.balans + promo_code.reward
            )
            await session.execute(stmt)
            
            await session.commit()
            
            # Получаем обновленные данные для логирования
            updated_user = await get_user(user_id)
            updated_promo = await get_promo_code(promo_code.code)
            
            logger.info(
                f"Промокод {promo_code.code} успешно активирован:\n"
                f"- Пользователь: {user_id} (ID: {user.id})\n"
                f"- Активаций было: {old_activations}, стало: {updated_promo.current_activations}\n"
                f"- Баланс был: {old_balance}, стал: {updated_user.balans}\n"
                f"- Начислено: {promo_code.reward} ⭐"
            )
            return True

async def process_gift_withdrawal(user_id: int, gift_price: float) -> tuple[bool, float]:
    """
    Обрабатывает вывод подарка и списание звезд.
    
    Args:
        user_id (int): Telegram ID пользователя
        gift_price (float): Стоимость подарка
        
    Returns:
        tuple[bool, float]: (успех операции, новый баланс)
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # Получаем пользователя
            user = await get_user(user_id)
            if not user:
                return False, 0
                
            # Проверяем баланс
            if user.balans < gift_price:
                return False, user.balans
                
            # Списываем звезды
            stmt = update(db.User).where(
                db.User.id == user.id
            ).values(
                balans=db.User.balans - gift_price
            )
            await session.execute(stmt)
            await session.commit()
            
            return True, user.balans - gift_price
        

#Запросы для заданий 

async def get_active_chanels():
    """
    Получает список всех активных каналов.
    
    Returns:
        list: Список активных каналов
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.Chanel).where(db.Chanel.is_active == True)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_next_task(user_id: int):
    """
    Получает следующее доступное задание для пользователя.
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        Chanel: Следующее доступное задание или None, если заданий больше нет
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.Chanel).outerjoin(
            db.UserTask, (db.Chanel.id == db.UserTask.task_id) & (db.UserTask.user_id == user_id)
        ).where(
            (db.UserTask.id == None) | (db.UserTask.completed == False)
        ).order_by(db.Chanel.id)
        result = await session.execute(stmt)
        return result.scalars().first()

async def mark_task_completed(user_id: int, task_id: int):
    """
    Отмечает задание как выполненное.
    
    Args:
        user_id (int): ID пользователя
        task_id (int): ID задания
    """
    async with AsyncSessionFactory() as session:
        stmt = update(db.UserTask).where(
            (db.UserTask.user_id == user_id) & (db.UserTask.task_id == task_id)
        ).values(completed=True, completed_at=datetime.now())
        await session.execute(stmt)
        await session.commit()

async def decrease_channel_limit(channel_id: int):
    """
    Уменьшает лимит канала на 1 и деактивирует его, если лимит достиг 0.
    
    Args:
        channel_id (int): ID канала
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.Chanel).where(db.Chanel.id == channel_id)
        result = await session.execute(stmt)
        channel = result.scalars().first()

        if channel and channel.limit > 0:
            channel.limit -= 1
            if channel.limit == 0:
                channel.is_active = False
            await session.commit()

async def add_reward_to_user(user_id: int, reward: int):
    """
    Начисляет награду пользователю.
    
    Args:
        user_id (int): ID пользователя
        reward (int): Количество награды для начисления
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.User).where(db.User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        user.balans += reward
        await session.commit()

async def get_user_task(user_id: int, task_id: int):
    """
    Получает информацию о задании пользователя.
    
    Args:
        user_id (int): ID пользователя
        task_id (int): ID задания
        
    Returns:
        UserTask: Информация о задании пользователя или None, если задание не найдено
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.UserTask).where(
            db.UserTask.user_id == user_id, db.UserTask.task_id == task_id
        )
        result = await session.execute(stmt)
        return result.scalars().first()

async def add_user_task(user_id: int, task_id: int):
    """
    Добавляет новое задание пользователю.
    
    Args:
        user_id (int): ID пользователя
        task_id (int): ID задания
    """
    async with AsyncSessionFactory() as session:
        new_task = db.UserTask(user_id=user_id, task_id=task_id)
        session.add(new_task)
        await session.commit()

async def get_channel_by_task_id(task_id: int):
    """
    Получает информацию о канале по ID задания.
    
    Args:
        task_id (int): ID задания
        
    Returns:
        Chanel: Информация о канале или None, если канал не найден
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.Chanel).where(db.Chanel.id == task_id)
        result = await session.execute(stmt)
        return result.scalars().first()

async def get_active_sponsor_channels():
    """
    Получает список всех активных спонсорских каналов.
    
    Returns:
        list: Список активных спонсорских каналов
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.OPChannel).where(db.OPChannel.is_active == True)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_random_ad_post():
    """
    Получает случайный рекламный пост из базы данных и увеличивает счетчик показов.
    Использует одну сессию для получения поста и обновления счетчика.
    
    Returns:
        AdPost: Случайный рекламный пост или None, если постов нет
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # Получаем общее количество постов
            count = await session.execute(select(func.count(db.AdPost.id)))
            total = count.scalar_one()
            
            if total == 0:
                return None
                
            # Получаем случайный пост
            offset = random.randint(0, total - 1)
            stmt = select(db.AdPost).offset(offset).limit(1)
            result = await session.execute(stmt)
            post = result.scalar_one()
            
            if post:
                # Увеличиваем счетчик показов
                post.show_count += 1
                session.add(post)
                
                # Создаем запись о показе
                show = db.AdPostShow(post_id=post.id)
                session.add(show)
                
                await session.commit()
                
            return post

async def get_ad_post_stats():
    """
    Получает статистику по рекламным постам.
    
    Returns:
        List[dict]: Список постов со статистикой
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.AdPost).order_by(db.AdPost.show_count.desc())
        result = await session.execute(stmt)
        posts = result.scalars().all()
        
        return [{
            'id': post.id,
            'name': post.name,
            'show_count': post.show_count,
            'created_at': post.created_at
        } for post in posts]

async def get_users_stats():
    """
    Получает статистику по пользователям с разбивкой по периодам
    
    Returns:
        dict: Статистика пользователей
    """
    async with AsyncSessionFactory() as session:
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Общее количество пользователей
        total_users = await session.execute(select(func.count(db.User.id)))
        total_users = total_users.scalar_one() or 0
        
        # Новые пользователи по периодам
        new_users_day = await session.execute(
            select(func.count(db.User.id)).where(db.User.created_at >= day_ago)
        )
        new_users_week = await session.execute(
            select(func.count(db.User.id)).where(db.User.created_at >= week_ago)
        )
        new_users_month = await session.execute(
            select(func.count(db.User.id)).where(db.User.created_at >= month_ago)
        )
        
        return {
            "total_users": total_users,
            "new_users": {
                "day": new_users_day.scalar_one() or 0,
                "week": new_users_week.scalar_one() or 0,
                "month": new_users_month.scalar_one() or 0
            }
        }

async def get_ad_posts_stats():
    """
    Получает статистику по рекламным постам
    
    Returns:
        dict: Статистика рекламных постов
    """
    async with AsyncSessionFactory() as session:
        # Общее количество постов и показов
        total_posts = await session.execute(select(func.count(db.AdPost.id)))
        total_posts = total_posts.scalar_one() or 0
        
        # Общее количество показов
        total_shows = await session.execute(
            select(func.count(db.AdPostShow.id))
        )
        
        # Топ-3 поста по показам
        top_posts = await session.execute(
            select(db.AdPost)
            .order_by(db.AdPost.show_count.desc())
            .limit(3)
        )
        top_posts = top_posts.scalars().all()
        
        return {
            "total_posts": total_posts,
            "shows": {
                "total": total_shows.scalar_one() or 0
            },
            "top_posts": [{
                "name": post.name,
                "shows": post.show_count
            } for post in top_posts]
        }

async def get_promo_stats():
    """
    Получает статистику по промокодам с разбивкой по периодам
    
    Returns:
        dict: Статистика промокодов
    """
    async with AsyncSessionFactory() as session:
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Активные промокоды
        active_promos = await session.execute(
            select(func.count(db.PromoCode.id))
            .where(db.PromoCode.is_active == True)
        )
        active_promos = active_promos.scalar_one() or 0
        
        # Активации по периодам (все из таблицы PromoCodeActivation)
        activations_total = await session.execute(
            select(func.count(db.PromoCodeActivation.id))
        )
        activations_day = await session.execute(
            select(func.count(db.PromoCodeActivation.id))
            .where(db.PromoCodeActivation.activated_at >= day_ago)
        )
        activations_week = await session.execute(
            select(func.count(db.PromoCodeActivation.id))
            .where(db.PromoCodeActivation.activated_at >= week_ago)
        )
        activations_month = await session.execute(
            select(func.count(db.PromoCodeActivation.id))
            .where(db.PromoCodeActivation.activated_at >= month_ago)
        )
        
        return {
            "active_promos": active_promos,
            "activations": {
                "total": activations_total.scalar_one() or 0,
                "day": activations_day.scalar_one() or 0,
                "week": activations_week.scalar_one() or 0,
                "month": activations_month.scalar_one() or 0
            }
        }

async def get_channels_stats():
    """
    Получает статистику по заданиям с разбивкой по периодам
    
    Returns:
        dict: Статистика заданий
    """
    async with AsyncSessionFactory() as session:
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Выполненные задания по периодам
        completed_total = await session.execute(
            select(func.count(db.UserTask.id))
            .where(db.UserTask.completed == True)
        )
        completed_today = await session.execute(
            select(func.count(db.UserTask.id))
            .where(
                and_(
                    db.UserTask.completed == True,
                    db.UserTask.completed_at >= day_ago
                )
            )
        )
        completed_week = await session.execute(
            select(func.count(db.UserTask.id))
            .where(
                and_(
                    db.UserTask.completed == True,
                    db.UserTask.completed_at >= week_ago
                )
            )
        )
        completed_month = await session.execute(
            select(func.count(db.UserTask.id))
            .where(
                and_(
                    db.UserTask.completed == True,
                    db.UserTask.completed_at >= month_ago
                )
            )
        )
        
        return {
            "completed_tasks": {
                "total": completed_total.scalar_one() or 0,
                "today": completed_today.scalar_one() or 0,
                "week": completed_week.scalar_one() or 0,
                "month": completed_month.scalar_one() or 0
            }
        }

async def create_promo_code(code: str, reward: float, max_activations: int) -> bool:
    """
    Создает новый промокод в базе данных.
    
    Args:
        code (str): Код промокода
        reward (float): Количество звезд для награды
        max_activations (int): Максимальное количество активаций
        
    Returns:
        bool: True если промокод успешно создан, False если произошла ошибка
    """
    try:
        async with AsyncSessionFactory() as session:
            # Проверяем, не существует ли уже такой промокод
            existing = await get_promo_code(code)
            if existing:
                logger.warning(f"Попытка создать существующий промокод: {code}")
                return False
                
            # Создаем новый промокод
            new_promo = db.PromoCode(
                code=code,
                reward=reward,
                max_activations=max_activations,
                current_activations=0,
                is_active=True
            )
            session.add(new_promo)
            await session.commit()
            
            logger.info(
                f"Создан новый промокод:\n"
                f"- Код: {code}\n"
                f"- Награда: {reward} ⭐\n"
                f"- Макс. активаций: {max_activations}"
            )
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при создании промокода {code}: {e}")
        return False

async def check_promo_code_exists(code: str) -> bool:
    """
    Проверяет, существует ли промокод с таким кодом.
    
    Args:
        code (str): Код промокода для проверки
        
    Returns:
        bool: True если промокод существует, False если нет
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.PromoCode).where(db.PromoCode.code == code)
        result = await session.execute(stmt)
        return result.first() is not None

async def create_referral_link(name: str, admin_id: int) -> tuple[bool, str, str]:
    """
    Создает новую реферальную ссылку.
    
    Args:
        name (str): Название ссылки
        admin_id (int): ID админа, создающего ссылку
        
    Returns:
        tuple[bool, str, str]: (успех операции, код ссылки, сообщение об ошибке)
    """
    try:
        async with AsyncSessionFactory() as session:
            # Генерируем уникальный код
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                # Проверяем, не существует ли уже такой код
                stmt = select(db.ReferralLink).where(db.ReferralLink.code == code)
                result = await session.execute(stmt)
                if not result.first():
                    break
            
            # Получаем внутренний ID админа
            stmt = select(db.User).where(db.User.user_id == admin_id)
            result = await session.execute(stmt)
            admin = result.scalar_one()
            
            if not admin:
                return False, "", "Админ не найден в базе данных"
            
            # Создаем новую ссылку
            new_link = db.ReferralLink(
                name=name,
                code=code,
                created_by=admin.id
            )
            session.add(new_link)
            await session.commit()
            
            logger.info(
                f"Создана новая реферальная ссылка:\n"
                f"- Название: {name}\n"
                f"- Код: {code}\n"
                f"- Создал: {admin_id}"
            )
            
            return True, code, ""
            
    except Exception as e:
        logger.error(f"Ошибка при создании реферальной ссылки: {e}")
        return False, "", str(e)

async def get_referral_link(code: str) -> Optional[db.ReferralLink]:
    """
    Получает информацию о реферальной ссылке по коду.
    
    Args:
        code (str): Код реферальной ссылки
        
    Returns:
        Optional[ReferralLink]: Информация о ссылке или None, если ссылка не найдена
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.ReferralLink).where(
            db.ReferralLink.code == code,
            db.ReferralLink.is_active == True
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def increment_referral_link_uses(code: str) -> bool:
    """
    Увеличивает счетчик использований реферальной ссылки.
    
    Args:
        code (str): Код реферальной ссылки
        
    Returns:
        bool: True если операция успешна, False если ссылка не найдена
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.ReferralLink).where(db.ReferralLink.code == code)
            result = await session.execute(stmt)
            link = result.scalar_one_or_none()
            
            if not link:
                return False
                
            link.uses_count += 1
            link.last_used_at = datetime.now()
            await session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении счетчика использований ссылки {code}: {e}")
        return False

async def get_admin_ref_links(admin_id: int, page: int = 0, per_page: int = 8) -> tuple[list, int]:
    """
    Получает список реферальных ссылок админа с пагинацией
    
    Args:
        admin_id (int): ID админа
        page (int): Номер страницы (начиная с 0)
        per_page (int): Количество ссылок на странице
        
    Returns:
        tuple[list, int]: (список ссылок для текущей страницы, общее количество страниц)
    """
    async with AsyncSessionFactory() as session:
        # Получаем внутренний ID админа
        stmt = select(db.User).where(db.User.user_id == admin_id)
        result = await session.execute(stmt)
        admin = result.scalar_one()
        
        if not admin:
            return [], 0
        
        # Получаем общее количество ссылок
        total = await session.execute(
            select(func.count(db.ReferralLink.id))
            .where(db.ReferralLink.created_by == admin.id)
        )
        total = total.scalar_one() or 0
        
        # Вычисляем общее количество страниц
        total_pages = (total + per_page - 1) // per_page
        
        # Получаем ссылки для текущей страницы
        stmt = select(db.ReferralLink).where(
            db.ReferralLink.created_by == admin.id
        ).order_by(
            db.ReferralLink.created_at.desc()
        ).offset(page * per_page).limit(per_page)
        
        result = await session.execute(stmt)
        links = result.scalars().all()
        
        # Формируем список словарей с информацией о ссылках
        links_data = [{
            'id': link.id,
            'name': link.name,
            'code': link.code,
            'uses_count': link.uses_count,
            'last_used_at': link.last_used_at,
            'is_active': link.is_active,
            'created_at': link.created_at
        } for link in links]
        
        return links_data, total_pages

async def get_ref_link_details(link_id: int) -> Optional[dict]:
    """
    Получает детальную информацию о реферальной ссылке
    
    Args:
        link_id (int): ID реферальной ссылки
        
    Returns:
        Optional[dict]: Информация о ссылке или None, если ссылка не найдена
    """
    async with AsyncSessionFactory() as session:
        stmt = select(db.ReferralLink).where(db.ReferralLink.id == link_id)
        result = await session.execute(stmt)
        link = result.scalar_one_or_none()
        
        if not link:
            return None
            
        # Получаем информацию о создателе
        stmt = select(db.User).where(db.User.id == link.created_by)
        result = await session.execute(stmt)
        creator = result.scalar_one()
        
        return {
            'id': link.id,
            'name': link.name,
            'code': link.code,
            'uses_count': link.uses_count,
            'last_used_at': link.last_used_at,
            'is_active': link.is_active,
            'created_at': link.created_at,
            'creator': {
                'user_id': creator.user_id,
                'username': creator.username
            } if creator else None
        }

async def toggle_ref_link_status(link_id: int) -> bool:
    """
    Переключает статус активности реферальной ссылки
    
    Args:
        link_id (int): ID реферальной ссылки
        
    Returns:
        bool: True если операция успешна, False если ссылка не найдена
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.ReferralLink).where(db.ReferralLink.id == link_id)
            result = await session.execute(stmt)
            link = result.scalar_one_or_none()
            
            if not link:
                return False
                
            # Инвертируем статус
            link.is_active = not link.is_active
            await session.commit()
            
            logger.info(
                f"Изменен статус реферальной ссылки {link.code}:\n"
                f"- Новый статус: {'активна' if link.is_active else 'деактивирована'}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса ссылки {link_id}: {e}")
        return False

async def get_all_op_channels() -> list:
    """Получает список всех ОП каналов"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(db.OPChannel).order_by(db.OPChannel.id)
        )
        channels = result.scalars().all()
        return [
            {
                'id': channel.id,
                'name': channel.name,
                'channel_id': channel.channel_id,
                'url': channel.url,
                'is_active': channel.is_active,
                'limit': channel.limit
            }
            for channel in channels
        ]

async def get_op_channel(channel_id: int) -> Optional[dict]:
    """Получает информацию об ОП канале по его ID"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(db.OPChannel).where(db.OPChannel.id == channel_id)
        )
        channel = result.scalar_one_or_none()
        if channel:
            return {
                'id': channel.id,
                'name': channel.name,
                'channel_id': channel.channel_id,
                'url': channel.url,
                'is_active': channel.is_active,
                'limit': channel.limit
            }
        return None

async def add_op_channel(name: str, channel_id: int, url: str) -> tuple[bool, str]:
    """
    Добавляет новый ОП канал
    
    Args:
        name (str): Название канала
        channel_id (int): ID канала в Telegram
        url (str): URL канала
        
    Returns:
        tuple[bool, str]: (успех операции, сообщение об ошибке)
    """
    try:
        async with AsyncSessionFactory() as session:
            # Проверяем, не существует ли уже канал с таким ID
            stmt = select(db.OPChannel).where(db.OPChannel.channel_id == channel_id)
            result = await session.execute(stmt)
            if result.first():
                return False, "Канал с таким ID уже существует"
            
            # Создаем новый канал
            new_channel = db.OPChannel(
                name=name,
                channel_id=channel_id,
                url=url,
                is_active=True
            )
            session.add(new_channel)
            await session.commit()
            
            logger.info(
                f"Добавлен новый ОП канал:\n"
                f"- Название: {name}\n"
                f"- ID: {channel_id}\n"
                f"- URL: {url}"
            )
            
            return True, ""
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении ОП канала: {e}")
        return False, str(e)

async def delete_op_channel(channel_id: int) -> bool:
    """
    Удаляет ОП канал
    
    Args:
        channel_id (int): ID канала
        
    Returns:
        bool: True если операция успешна, False если канал не найден
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.OPChannel).where(db.OPChannel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            
            if not channel:
                return False
                
            await session.delete(channel)
            await session.commit()
            
            logger.info(f"Удален ОП канал: {channel.name} (ID: {channel.channel_id})")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при удалении ОП канала {channel_id}: {e}")
        return False

async def toggle_op_channel_status(channel_id: int) -> bool:
    """
    Переключает статус активности ОП канала
    
    Args:
        channel_id (int): ID канала
        
    Returns:
        bool: True если операция успешна, False если канал не найден
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.OPChannel).where(db.OPChannel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            
            if not channel:
                return False
                
            # Инвертируем статус
            channel.is_active = not channel.is_active
            await session.commit()
            
            logger.info(
                f"Изменен статус ОП канала {channel.name}:\n"
                f"- Новый статус: {'активен' if channel.is_active else 'деактивирован'}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса ОП канала {channel_id}: {e}")
        return False

async def get_all_task_channels() -> list:
    """Получает список всех каналов заданий со статистикой выполнений"""
    async with AsyncSessionFactory() as session:
        # Получаем каналы и считаем количество выполненных заданий для каждого
        stmt = select(
            db.Chanel,
            func.sum(case((db.UserTask.completed == True, 1), else_=0)).label('completed_count')
        ).outerjoin(
            db.UserTask,
            db.Chanel.id == db.UserTask.task_id
        ).group_by(
            db.Chanel.id
        ).order_by(db.Chanel.id)
        
        result = await session.execute(stmt)
        channels = result.all()
        
        return [{
            'id': channel.Chanel.id,
            'name': channel.Chanel.chanel_name,
            'channel_id': channel.Chanel.chanel_id,
            'url': channel.Chanel.link,
            'is_active': channel.Chanel.is_active,
            'total_limit': channel.Chanel.limit + int(channel.completed_count or 0),  # Общее количество заданий
            'current_limit': channel.Chanel.limit,  # Текущий оставшийся лимит
            'reward': channel.Chanel.reward,
            'completed_count': int(channel.completed_count or 0)
        } for channel in channels]

async def get_task_channel(channel_id: int) -> Optional[dict]:
    """Получает информацию о канале заданий по его ID"""
    async with AsyncSessionFactory() as session:
        # Получаем канал и считаем количество выполненных заданий
        stmt = select(
            db.Chanel,
            func.sum(case((db.UserTask.completed == True, 1), else_=0)).label('completed_count')
        ).outerjoin(
            db.UserTask,
            db.Chanel.id == db.UserTask.task_id
        ).where(
            db.Chanel.id == channel_id
        ).group_by(
            db.Chanel.id
        )
        
        result = await session.execute(stmt)
        channel = result.first()
        
        if channel:
            return {
                'id': channel.Chanel.id,
                'name': channel.Chanel.chanel_name,
                'channel_id': channel.Chanel.chanel_id,
                'url': channel.Chanel.link,
                'is_active': channel.Chanel.is_active,
                'total_limit': channel.Chanel.limit + int(channel.completed_count or 0),  # Общее количество заданий
                'current_limit': channel.Chanel.limit,  # Текущий оставшийся лимит
                'reward': channel.Chanel.reward,
                'completed_count': int(channel.completed_count or 0)
            }
        return None

async def add_task_channel(name: str, channel_id: int, url: str, limit: int, reward: float) -> tuple[bool, str]:
    """
    Добавляет новый канал заданий
    
    Args:
        name (str): Название канала
        channel_id (int): ID канала в Telegram
        url (str): URL канала
        limit (int): Лимит выполнений
        reward (float): Награда за выполнение
        
    Returns:
        tuple[bool, str]: (успех операции, сообщение об ошибке)
    """
    try:
        async with AsyncSessionFactory() as session:
            # Проверяем, не существует ли уже канал с таким ID
            stmt = select(db.Chanel).where(db.Chanel.chanel_id == channel_id)
            result = await session.execute(stmt)
            if result.first():
                return False, "Канал с таким ID уже существует"
            
            # Создаем новый канал
            new_channel = db.Chanel(
                chanel_name=name,
                chanel_id=channel_id,
                link=url,
                limit=limit,
                reward=reward,
                is_active=True
            )
            session.add(new_channel)
            await session.commit()
            
            logger.info(
                f"Добавлен новый канал заданий:\n"
                f"- Название: {name}\n"
                f"- ID: {channel_id}\n"
                f"- URL: {url}\n"
                f"- Лимит: {limit}\n"
                f"- Награда: {reward} ⭐"
            )
            
            return True, ""
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении канала заданий: {e}")
        return False, str(e)

async def delete_task_channel(channel_id: int) -> bool:
    """
    Удаляет канал заданий
    
    Args:
        channel_id (int): ID канала
        
    Returns:
        bool: True если операция успешна, False если канал не найден
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.Chanel).where(db.Chanel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            
            if not channel:
                return False
                
            await session.delete(channel)
            await session.commit()
            
            logger.info(f"Удален канал заданий: {channel.chanel_name} (ID: {channel.chanel_id})")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при удалении канала заданий {channel_id}: {e}")
        return False

async def toggle_task_channel_status(channel_id: int) -> bool:
    """
    Переключает статус активности канала заданий
    
    Args:
        channel_id (int): ID канала
        
    Returns:
        bool: True если операция успешна, False если канал не найден
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.Chanel).where(db.Chanel.id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            
            if not channel:
                return False
                
            # Инвертируем статус
            channel.is_active = not channel.is_active
            await session.commit()
            
            logger.info(
                f"Изменен статус канала заданий {channel.chanel_name}:\n"
                f"- Новый статус: {'активен' if channel.is_active else 'деактивирован'}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса канала заданий {channel_id}: {e}")
        return False

async def get_referral_reward() -> float:
    """Получить текущую награду за реферала"""
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(db.Settings))
            settings = result.scalar_one_or_none()
            if not settings:
                # Если настроек нет, создаем с дефолтным значением
                settings = db.Settings(referral_reward=3.0)
                session.add(settings)
                await session.commit()
            return settings.referral_reward
    except Exception as e:
        logging.error(f"Error getting referral reward: {e}")
        return 3.0  # Возвращаем дефолтное значение в случае ошибки

async def update_referral_reward(new_reward: float) -> bool:
    """Обновить награду за реферала"""
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(db.Settings))
            settings = result.scalar_one_or_none()
            
            if settings:
                settings.referral_reward = new_reward
            else:
                settings = db.Settings(referral_reward=new_reward)
                session.add(settings)
            
            await session.commit()
            return True
    except Exception as e:
        logging.error(f"Error updating referral reward: {e}")
        return False

async def get_current_referral_reward() -> float:
    """
    Получает текущую награду за реферала из настроек.
    
    Returns:
        float: Текущая награда за реферала (по умолчанию 3.0)
    """
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(db.Settings).order_by(db.Settings.id.desc()).limit(1))
            settings = result.scalar_one_or_none()
            return settings.referral_reward if settings else 3.0
    except Exception as e:
        logger.error(f"Ошибка при получении награды за реферала: {e}")
        return 3.0  # Возвращаем дефолтное значение в случае ошибки

async def get_all_ad_posts() -> list:
    """Получает список всех рекламных постов"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(db.AdPost).order_by(db.AdPost.id.desc())
        )
        posts = result.scalars().all()
        return [{
            'id': post.id,
            'name': post.name,
            'show_count': post.show_count,
            'created_at': post.created_at
        } for post in posts]

async def get_ad_post(post_id: int) -> Optional[dict]:
    """Получает информацию о рекламном посте по его ID"""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(db.AdPost).where(db.AdPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        if post:
            return {
                'id': post.id,
                'name': post.name,
                'text': post.text,
                'url': post.url,
                'show_count': post.show_count,
                'created_at': post.created_at
            }
        return None

async def add_ad_post(name: str, text: str, url: Optional[str] = None) -> tuple[bool, str]:
    """
    Добавляет новый рекламный пост
    
    Args:
        name (str): Название поста
        text (str): Текст поста
        url (Optional[str]): URL для кнопки
        
    Returns:
        tuple[bool, str]: (успех операции, сообщение об ошибке)
    """
    try:
        async with AsyncSessionFactory() as session:
            # Создаем новый пост
            new_post = db.AdPost(
                name=name,
                text=text,
                url=url
            )
            session.add(new_post)
            await session.commit()
            
            logger.info(
                f"Добавлен новый рекламный пост:\n"
                f"- Название: {name}\n"
                f"- URL: {url if url else 'нет'}"
            )
            
            return True, ""
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении рекламного поста: {e}")
        return False, str(e)

async def delete_ad_post(post_id: int) -> bool:
    """
    Удаляет рекламный пост и все связанные с ним записи
    
    Args:
        post_id (int): ID поста
        
    Returns:
        bool: True если операция успешна, False если пост не найден
    """
    try:
        async with AsyncSessionFactory() as session:
            async with session.begin():
                
                # Затем удаляем сам пост
                stmt = select(db.AdPost).where(db.AdPost.id == post_id)
                result = await session.execute(stmt)
                post = result.scalar_one_or_none()
                
                if not post:
                    return False
                    
                await session.delete(post)
                await session.commit()
                
                logger.info(f"Удален рекламный пост: {post.name} (ID: {post.id})")
                return True
            
    except Exception as e:
        logger.error(f"Ошибка при удалении рекламного поста {post_id}: {e}")
        return False

async def toggle_ad_post_status(post_id: int) -> bool:
    """
    Переключает статус активности рекламного поста
    
    Args:
        post_id (int): ID поста
        
    Returns:
        bool: True если операция успешна, False если пост не найден
    """
    try:
        async with AsyncSessionFactory() as session:
            stmt = select(db.AdPost).where(db.AdPost.id == post_id)
            result = await session.execute(stmt)
            post = result.scalar_one_or_none()
            
            if not post:
                return False
                
            # Инвертируем статус
            post.is_active = not post.is_active
            await session.commit()
            
            logger.info(
                f"Изменен статус рекламного поста {post.name}:\n"
                f"- Новый статус: {'активен' if post.is_active else 'деактивирован'}"
            )
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса рекламного поста {post_id}: {e}")
        return False

async def update_user_op_status(user_id: int, status: bool = True):
    """Обновляет статус прохождения опроса пользователем"""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            stmt = update(db.User).where(
                db.User.user_id == user_id
            ).values(op_status=status)
            await session.execute(stmt)
            await session.commit()

async def get_referral_stats(referral_code: str) -> dict:
    """Получает расширенную статистику по реферальной ссылке"""
    async with AsyncSessionFactory() as session:
        # Получаем всех пользователей с этой реферальной ссылкой
        stmt = select(db.User).where(db.User.referred_by == referral_code)
        result = await session.execute(stmt)
        users = result.scalars().all()
        
        total_users = len(users)
        completed_op = sum(1 for user in users if user.op_status)
        
        # Статистика по заданиям
        started_tasks = 0  # Начатые задания
        completed_tasks = 0  # Выполненные задания
        
        # Получаем все задания для всех рефералов одним запросом
        if users:
            telegram_ids = [user.user_id for user in users]  # Используем Telegram ID пользователя
            # Подсчитываем начатые задания
            started_stmt = select(func.count()).select_from(db.UserTask).where(
                db.UserTask.user_id.in_(telegram_ids)
            )
            started_result = await session.execute(started_stmt)
            started_tasks = started_result.scalar_one() or 0
            
            # Подсчитываем выполненные задания
            completed_stmt = select(func.count()).select_from(db.UserTask).where(
                and_(
                    db.UserTask.user_id.in_(telegram_ids),
                    db.UserTask.completed == True
                )
            )
            completed_result = await session.execute(completed_stmt)
            completed_tasks = completed_result.scalar_one() or 0
        
        return {
            "total_users": total_users,
            "completed_op": completed_op,
            "tasks": {
                "started": started_tasks,  # Общее количество начатых заданий
                "completed": completed_tasks,  # Количество выполненных заданий
                "in_progress": started_tasks - completed_tasks  # Задания в процессе
            }
        }

