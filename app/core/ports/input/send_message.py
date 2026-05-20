from abc import ABC, abstractmethod

from app.core.ports.dto import ChatRequestDTO, ChatResponseDTO


class SendMessageUseCase(ABC):
    """Порт для отправки сообщения"""
    
    @abstractmethod
    async def send_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        pass