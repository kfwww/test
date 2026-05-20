from abc import ABC, abstractmethod

from app.core.ports.dto import MessageDTO


class LLMClient(ABC):
    """Порт для клиента LLM"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, history: list[MessageDTO] | None = None) -> str:
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        pass