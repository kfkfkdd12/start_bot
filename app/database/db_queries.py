from sqlalchemy.future import select
from sqlalchemy import update, func, insert, delete
from datetime import datetime, timedelta
from . import database as db
from .database import AsyncSessionFactory
from sqlalchemy.exc import OperationalError
from typing import Optional, List
from config import Config
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
