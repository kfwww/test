import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.main import create_app
from app.core.services.chat_service import ChatService
from app.core.services.health_service import HealthService
from app.adapters.output.postgres_repository import PostgresMessageRepository, Base
from app.adapters.output.vllm_client import VLLMClient
from infrastructure.config.settings import settings


TEST_DB_NAME = 'test_chat_db'

TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.rsplit('/', 1)[-1],
    TEST_DB_NAME
)

ADMIN_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.DATABASE_URL.rsplit('/', 1)[-1],
    'postgres'
)


async def create_test_db():
    """Создать тестовую БД если не существует"""
    engine = create_async_engine(ADMIN_DATABASE_URL, echo=False, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
        )
        if not result.fetchone():
            await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def _create_test_db_once():
    """Создать тестовую БД один раз за сессию"""
    await create_test_db()
    yield


@pytest_asyncio.fixture(scope="function")
async def test_engine(_create_test_db_once):
    """Создать тестовый движок БД"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def message_repository(test_engine):
    """Создать репозиторий с тестовым engine"""
    repo = object.__new__(PostgresMessageRepository)
    repo.database_url = TEST_DATABASE_URL
    repo.engine = test_engine
    repo.async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    return repo


@pytest_asyncio.fixture(scope="function")
async def llm_client():
    """Создать реальный LLM клиент"""
    client = VLLMClient()
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="function")
async def chat_service(message_repository, llm_client):
    """Создать сервис чата"""
    return ChatService(message_repository, llm_client)


@pytest_asyncio.fixture(scope="function")
async def health_service(llm_client, message_repository):
    """Создать сервис проверки здоровья"""
    return HealthService(llm_client, message_repository)


@pytest_asyncio.fixture(scope="function")
async def app(chat_service, health_service):
    """Создать тестовое FastAPI приложение"""
    app = create_app()
    app.state.send_message_use_case = chat_service
    app.state.get_history_use_case = chat_service
    app.state.get_user_history_use_case = chat_service
    app.state.health_check_use_case = health_service
    return app


@pytest_asyncio.fixture(scope="function")
async def client(app):
    """Создать асинхронный HTTP клиент"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac