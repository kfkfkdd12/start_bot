import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, text, ForeignKey, Text, Boolean
from config import Config
from datetime import datetime
from dotenv import load_dotenv

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

class OPChannel(Base):
    __tablename__ = 'op_channels'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, index=True, nullable=False)
    url = Column(String(255))
    reward = Column(Float)
    name = Column(String(255))
    limit = Column(Integer, default=10000)
    is_active = Column(Boolean, default=True)


class TaskChannel(Base):
    __tablename__ = 'task_channels'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, index=True, nullable=False)
    url = Column(String(255))
    reward = Column(Float)
    name = Column(String(255))
    limit = Column(Integer, default=10000)
    is_active = Column(Boolean, default=True)


class AdPost(Base):
    __tablename__ = 'ad_posts'

    id = Column(Integer, primary_key=True)
    url = Column(String(255))
    text = Column(String(255))
