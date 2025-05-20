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

async def activate_promo_code(user_id: int, promo_code: db.PromoCode) -> bool:
    """Активировать промокод для пользователя"""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # Проверяем, не активировал ли пользователь этот промокод ранее
            if await check_promo_activation(user_id, promo_code.id):
                return False
            
            # Проверяем, не превышен ли лимит активаций
            if promo_code.current_activations >= promo_code.max_activations:
                return False
            
            # Создаем запись об активации
            activation = db.PromoCodeActivation(
                user_id=user_id,
                promo_code_id=promo_code.id
            )
            session.add(activation)
            
            # Увеличиваем счетчик активаций
            promo_code.current_activations += 1
            
            # Начисляем награду пользователю
            user = await get_user(user_id)
            if user:
                user.balans += promo_code.reward
                await session.commit()
                return True
            return False
