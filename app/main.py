import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.adapters.input.fastapi import create_app
from app.adapters.output.vllm_client import VLLMClient
from app.adapters.output.postgres_repository import PostgresMessageRepository
from app.core.services.chat_service import ChatService
from app.core.services.health_service import HealthService
from infrastructure.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл: создаём сервисы при старте, закрываем при остановке"""
    print("=" * 50)
    print("Starting up services...")
    
    repository = PostgresMessageRepository(settings.DATABASE_URL)
    await repository.initialize()
    print("✓ Database initialized")
    
    llm_client = VLLMClient()
    print("✓ LLM client initialized")
    
    if await llm_client.is_available():
        print("✓ vLLM is available")
    else:
        print("⚠ vLLM is not available")
    
    chat_service = ChatService(repository, llm_client)
    health_service = HealthService(llm_client, repository)
    
    app.state.send_message_use_case = chat_service
    app.state.get_history_use_case = chat_service
    app.state.get_user_history_use_case = chat_service
    app.state.health_check_use_case = health_service
    
    app.state._llm_client = llm_client
    app.state._repository = repository
    
    print("=" * 50)
    print(f"API:  http://localhost:{settings.API_PORT}")
    print(f"Docs: http://localhost:{settings.API_PORT}/docs")
    print("=" * 50)
    
    yield
    
    print("Shutting down...")
    await llm_client.close()
    await repository.close()
    print("Done.")


def create_application() -> FastAPI:
    app = create_app()
    app.router.lifespan_context = lifespan
    return app


app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )