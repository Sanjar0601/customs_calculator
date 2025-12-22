from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.core.config import settings

# Создаем движок
engine = create_engine(settings.DATABASE_URL)

def create_db_and_tables():
    """Создает таблицы в БД, если их нет"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Генератор сессии для FastAPI"""
    with Session(engine) as session:
        yield session
        
