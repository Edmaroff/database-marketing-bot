from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import URL
from config_data.config import USERNAME_DB, HOST_DB, DATABASE_DB, PASSWORD_DB


def create_async_my_engine(url):
    """
    Создает асинхронный движок для взаимодействия с базой данных
    :param url: URL-адрес подключения к базе данных
    :return: Асинхронный движок для выполнения операций с базой данных
    - echo=True: Устанавливает вывод всех операций в базе данных для отладки
    - future=True: Использует асинхронные функции и классы для взаимодействия с БД
    - pool_pre_ping=True: Проверяет подключение к БД перед использованием из пула соединений
    """

    return create_async_engine(url, echo=False, future=True, pool_pre_ping=True)


def create_async_session(engine):
    """
    Создает асинхронную сессию для взаимодействия с базой данных
    :param engine: Асинхронный движок
    :return: Асинхронная сессия для выполнения операций с базой данных
    - expire_on_commit=True: Гарантирует получение актуальных данных при параллельных изменениях вБД
    """

    return async_sessionmaker(engine, expire_on_commit=True, class_=AsyncSession)


postgres_url = URL.create(
    "postgresql+asyncpg",
    username=USERNAME_DB,
    host=HOST_DB,
    database=DATABASE_DB,
    password=PASSWORD_DB,
)

# Создание движка для всего проекта
async_engine = create_async_my_engine(postgres_url)

# Создание сессии для всего проекта
async_session = create_async_session(async_engine)
