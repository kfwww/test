from abc import ABC, abstractmethod

from app.core.ports.dto import HealthResponse


class HealthCheckUseCase(ABC):
    """Порт для проверки здоровья сервиса"""
    
    @abstractmethod
    async def check_health(self) -> HealthResponse:
        """Проверить здоровье всех компонентов"""
        pass