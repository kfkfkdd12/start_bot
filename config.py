import os
from dotenv import load_dotenv

load_dotenv()

#fgfgf
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    ADMIN_IDS = [842912105, 923476599, 7635360930]  # Укажите здесь ID администраторов
 # Укажите здесь ID администраторов
    
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", 3306))  # Значение по умолчанию 3306
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")

    CHAT_URL = os.getenv("CHAT_URL")
    REVIEWS_URL = os.getenv("REVIEWS_URL")
    LOG = os.getenv("LOG")
    OTZIVI_URL = os.getenv("OTZIVI_URL")

    
    DATABASE_URL = (
        f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
