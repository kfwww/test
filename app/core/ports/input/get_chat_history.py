from abc import ABC, abstractmethod
from uuid import UUID

from app.core.ports.dto import SessionChatHistory, UserChatHistory


class GetChatHistoryUseCase(ABC):
    """Порт для получения истории чата"""
    
    @abstractmethod
    async def get_session_history(self, session_id: UUID) -> SessionChatHistory:
        pass

    @abstractmethod
    async def get_user_history(self, user_id: UUID) -> UserChatHistory:
        pass