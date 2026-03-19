from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from typing import AsyncGenerator

# 1. 声明引擎占位符，不立即初始化
_engine = None
_session_maker = None

def get_async_engine():
    """生产级：确保引擎在当前事件循环中按需初始化"""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL, 
            echo=True, 
            future=True,
            pool_pre_ping=True, # 生产级：自动检查断连
            pool_recycle=3600   # 生产级：每小时回收连接
        )
    return _engine

def get_async_sessionmaker():
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(
            get_async_engine(), 
            class_=AsyncSession, 
            expire_on_commit=False
        )
    return _session_maker

async def init_db():
    """初始化数据库表结构"""
    from app.core import models # 延迟导入
    from sqlmodel import SQLModel
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入入口"""
    async_session_maker = get_async_sessionmaker()
    async with async_session_maker() as session:
        yield session
