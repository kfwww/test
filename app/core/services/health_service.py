from app.core.ports.input.health_check import HealthCheckUseCase
from app.core.ports.output.llm_client import LLMClient
from app.core.ports.output.message_repository import MessageRepository
from app.core.ports.dto import HealthResponse


class HealthService(HealthCheckUseCase):
    """Сервис проверки здоровья"""
    
    def __init__(self, llm_client: LLMClient, message_repository: MessageRepository):
        self._llm_client = llm_client
        self._message_repository = message_repository
    
    async def check_health(self) -> HealthResponse:
        """Проверить здоровье всех компонентов"""
        vllm_available = await self._llm_client.is_available()
        database_available = await self._message_repository.is_available()
        
        status = "healthy" if (vllm_available and database_available) else "degraded"
        
        return HealthResponse(
            status=status,
            vllm_available=vllm_available,
            database_available=database_available
        )