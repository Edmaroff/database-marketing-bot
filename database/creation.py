from database.models import Base, ContentPlan
from database.engine import async_engine
import asyncio


async def create_tables(engine):
    """
    Создает таблицы в БД
    :param engine: Асинхронный движок для выполнения операций с БД.
    :return: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine):
    """
    Удаляет таблицы из БД.
    :param engine: Асинхронный движок для выполнения операций с БД.
    :return: None
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def create_table_content_plan(engine):
    """
    Создает таблицу content_plan в БД при уже существующих таблицах.
    :param engine: Асинхронный движок для выполнения операций с БД.
    """
    async with engine.begin() as conn:
        await conn.run_sync(ContentPlan.__table__.create)


async def drop_table_content_plan(engine):
    """
    Удаляет таблицу content_plan в БД при уже существующих таблицах.
    :param engine: Асинхронный движок для выполнения операций с БД.
    """
    async with engine.begin() as conn:
        await conn.run_sync(ContentPlan.__table__.drop)


# Создает все таблицы
# asyncio.run(create_tables(async_engine))

# Удаляет все таблицы
# asyncio.run(drop_tables(async_engine))

# # Создает таблицу ContentPlan
# asyncio.run(create_table_content_plan(async_engine))

# Удаляет таблицу ContentPlan
# asyncio.run(drop_table_content_plan(async_engine))
