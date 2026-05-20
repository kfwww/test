from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

from app.core.models.message import MessageRole
from infrastructure.utils import utc_now, generate_uuid
from app.core.models.message import Message


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    user_id: UUID | None = None


class ChatResponse(BaseModel):
    session_id: UUID
    user_message: MessageResponse
    assistant_message: MessageResponse


class SessionChatHistory(BaseModel):
    session_id: UUID
    messages: list[MessageResponse]


class UserChatHistory(BaseModel):
    """История всех чатов пользователя"""
    user_id: UUID
    sessions: list[SessionChatHistory]


class HealthResponse(BaseModel):
    status: str
    vllm_available: bool
    database_available: bool


@dataclass(frozen=True)
class MessageDTO:
    """DTO для передачи данных между сервисами и адаптерами"""
    id: UUID = field(default_factory=generate_uuid)
    session_id: UUID = field(default_factory=generate_uuid)
    role: MessageRole = MessageRole.USER
    content: str = ""
    created_at: datetime = field(default_factory=utc_now)
    user_id: UUID | None = None
    
    @classmethod
    def create_user_message(cls, session_id: UUID, content: str, user_id: UUID | None = None) -> "MessageDTO":
        """Создать DTO для сообщения пользователя"""
        return cls(
            id=generate_uuid(),
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
            user_id=user_id,
            created_at=utc_now()
        )
    
    @classmethod
    def create_assistant_message(cls, session_id: UUID, content: str, user_id: UUID | None = None) -> "MessageDTO":
        """Создать DTO для сообщения ассистента"""
        return cls(
            id=generate_uuid(),
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
            user_id=user_id,
            created_at=utc_now()
        )
    
    @classmethod
    def from_domain(cls, message: Message) -> "MessageDTO":
        """Создание DTO из доменной модели (если используется)"""
        return cls(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            user_id=getattr(message, 'user_id', None)
        )
    
    def to_response(self) -> MessageResponse:
        """Преобразование в Pydantic модель для API ответа"""
        return MessageResponse(
            id=self.id,
            session_id=self.session_id,
            role=self.role,
            content=self.content,
            created_at=self.created_at,
            user_id=self.user_id
        )
    
    def to_dict_for_llm(self) -> dict:
        """Преобразование в словарь для LLM (роль + контент)"""
        return {
            "role": self.role.value,
            "content": self.content
        }


@dataclass(frozen=True)
class ChatRequestDTO:
    """DTO для входящего запроса чата (из API в сервис)"""
    message: str
    session_id: UUID | None = None
    user_id: UUID | None = None
    
    @classmethod
    def from_request(cls, request: ChatRequest) -> "ChatRequestDTO":
        """Создание из API запроса"""
        return cls(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id
        )


@dataclass(frozen=True)
class ChatResponseDTO:
    """DTO для ответа чата (из сервиса в API)"""
    session_id: UUID
    user_message: MessageDTO
    assistant_message: MessageDTO
    
    def to_response(self) -> ChatResponse:
        """Преобразование в API ответ"""
        return ChatResponse(
            session_id=self.session_id,
            user_message=self.user_message.to_response(),
            assistant_message=self.assistant_message.to_response()
        )