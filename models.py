from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship

PG_DSN = 'postgresql+asyncpg://postgres:Tehn89tehn@127.0.0.1:5432/ads'
engine = create_async_engine(PG_DSN)
Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    """
    Таблица пользователей
    """
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(length=40), nullable=True, unique=True, index=True)
    password = Column(String, nullable=True)
    creationdate = Column(DateTime, server_default=func.now())
class AdsTable(Base):
    """
    Таблица объявлений
    """
    __tablename__ = 'adstable'

    id = Column(Integer, primary_key=True, autoincrement=True)
    head = Column(String(length=100), nullable=True, index=True)
    description = Column(String(length=500))
    creationdate = Column(DateTime, server_default=func.now())
    username = Column(Integer, ForeignKey('user.id'), nullable=True)

    user = relationship(User, backref='adstable')
