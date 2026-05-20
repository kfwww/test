from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any

from app.core.ports.dto import MessageDTO

class MessageRepository(ABC):
    """Порт для репозитория сообщений"""
    
    @abstractmethod
    async def save_user_message(self, session_id: UUID, content: str, user_id: UUID | None = None) -> MessageDTO:
        pass
    
    @abstractmethod
    async def save_assistant_message(self, session_id: UUID, content: str, user_id: UUID | None = None) -> MessageDTO:
        pass
    
    @abstractmethod
    async def get_by_session_id(self, session_id: UUID) -> list[MessageDTO]:
        pass
    
    @abstractmethod
    async def session_exists(self, session_id: UUID) -> bool:
        pass

    @abstractmethod
    async def user_exists(self, user_id: UUID) -> bool:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    @abstractmethod
    async def get_user_history_grouped(self, user_id: UUID) -> dict[UUID, list[MessageDTO]]:
        pass