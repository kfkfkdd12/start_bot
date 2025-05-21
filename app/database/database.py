import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, text, ForeignKey, Text, Boolean
from config import Config
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import relationship

load_dotenv()

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_async_engine(Config.DATABASE_URL, echo=False)
AsyncSessionFactory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def create_all_tables():
    """
    Создает все таблицы в базе данных
    """
    logger.info("Creating tables...")
    logger.info(f"Available tables: {Base.metadata.tables.keys()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables created successfully!")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    referred_by = Column(String(255), index=True)
    op_status = Column(Boolean, default=False)
    balans = Column(Float, default=0)
    deposit = Column(Float, default=0)


class OPChannel(Base):
    __tablename__ = 'op_channels'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, index=True, nullable=False)
    url = Column(String(255))
    name = Column(String(255))
    limit = Column(Integer, default=10000)
    is_active = Column(Boolean, default=True)


class Chanel(Base):
    __tablename__ = 'chanels'
    
    id = Column(Integer, primary_key=True)
    chanel_id = Column(BigInteger, unique=True, index=True, nullable=False)
    chanel_name = Column(String(255))
    link = Column(String(255))
    note = Column(String(255))
    is_active = Column(Boolean, default=True)
    sab = Column(Boolean, default=True)
    limit = Column(BigInteger)
    reward = Column(Float)

class UserTask(Base):
    __tablename__ = 'user_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    task_id = Column(Integer, nullable=False, index=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)


class AdPostShow(Base):
    """Таблица для отслеживания показов рекламных постов"""
    __tablename__ = 'ad_post_shows'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, nullable=False)
    shown_at = Column(DateTime, default=datetime.now, nullable=False)

class AdPost(Base):
    __tablename__ = 'ad_posts'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # Название поста для админа
    url = Column(String(255))
    text = Column(String(255))
    show_count = Column(Integer, default=0)  # Счетчик показов
    created_at = Column(DateTime, default=datetime.now)  # Дата создания поста


class PromoCode(Base):
    __tablename__ = "promo_codes"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    reward = Column(Float, nullable=False)  # Количество звезд
    max_activations = Column(Integer, nullable=False)  # Максимальное количество активаций
    current_activations = Column(Integer, default=0)  # Текущее количество активаций
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)  # Активен ли промокод

class PromoCodeActivation(Base):
    __tablename__ = "promo_code_activations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=False)
    activated_at = Column(DateTime, default=datetime.utcnow)

class ReferralLink(Base):
    """Таблица для хранения реферальных ссылок"""
    __tablename__ = 'referral_links'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)  # Название ссылки
    code = Column(String(50), unique=True, nullable=False)  # Уникальный код ссылки
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # ID админа, создавшего ссылку
    is_active = Column(Boolean, default=True)  # Активна ли ссылка
    uses_count = Column(Integer, default=0)  # Количество использований
    last_used_at = Column(DateTime)  # Последнее использование


class Settings(Base):
    """Таблица для хранения настроек бота"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    referral_reward = Column(Float, nullable=False, default=3.0)  # Награда за реферала
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now) 
    
