from sqlalchemy.future import select
from sqlalchemy import update, func, insert, delete
from datetime import datetime, timedelta
import stars_bot.app.database.database as db
from stars_bot.app.database.database import AsyncSessionFactory, User, OP1Channel, OP2Channel, OP1Text, OP2Text, WelcomeMessage, FinalMessage, ReferralLink, Autopost, AutopostSent
from sqlalchemy.exc import OperationalError
from typing import Optional, List
from stars_bot.config import Config
import random
import string
from sqlalchemy import and_

async def register_user(user_id: int, username: str, referred_by: str):
    """
    Регистрирует нового пользователя в базе данных.
    
    Args:
        user_id (int): ID пользователя в Telegram
        username (str): Username пользователя
        referred_by (str): Username пользователя, который пригласил
        
    Returns:
        bool: True если пользователь успешно зарегистрирован, False если пользователь уже существует
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            stmt = select(db.User).filter(db.User.user_id == user_id)
            result = await session.execute(stmt)
            user = result.scalars().first()
            if user:
                return False
            else:
                 new_user = db.User(
                user_id=user_id, 
                username=username,
                referred_by=referred_by,
                created_at=datetime.now()
            )
            session.add(new_user)
            await session.commit()
            return True
        
async def get_all_users():
    """
    Получает список всех пользователей из базы данных.
    
    Returns:
        List[User]: Список всех пользователей
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            stmt = select(User)
            result = await session.execute(stmt)
            return result.scalars().all()


async def get_user_by_id(user_id: int):
    """
    Получает пользователя по его ID.
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        User: Пользователь
    """
    async with AsyncSessionFactory() as session:
        async with session.begin():
            stmt = select(User).filter(User.user_id == user_id)
            result = await session.execute(stmt)
            return result.scalars().first()


