from uuid import UUID

from infrastructure.utils import generate_uuid
from app.core.ports.input.send_message import SendMessageUseCase
from app.core.ports.input.get_chat_history import GetChatHistoryUseCase
from app.core.ports.output.message_repository import MessageRepository
from app.core.ports.output.llm_client import LLMClient
from app.core.ports.dto import (
    ChatRequestDTO,
    ChatResponseDTO,
    UserChatHistory, SessionChatHistory
)


class ChatService(SendMessageUseCase, GetChatHistoryUseCase):
    """Основной сервис чата - работает только с DTO"""
    
    def __init__(self, message_repository: MessageRepository, llm_client: LLMClient):
        self._message_repository = message_repository
        self._llm_client = llm_client
    
    async def send_message(self, request: ChatRequestDTO) -> ChatResponseDTO:
        """
        Отправить сообщение модели и сохранить диалог
        
        Работает только с DTO, не зависит от доменных моделей
        """
        session_id = request.session_id if request.session_id else generate_uuid()
        
        user_message_dto = await self._message_repository.save_user_message(
            session_id=session_id,
            content=request.message,
            user_id=request.user_id
        )
        
        history_dtos = await self._message_repository.get_by_session_id(session_id)
        
        llm_response = await self._llm_client.generate_response(
            request.message,
            history=history_dtos
        )
        
        assistant_message_dto = await self._message_repository.save_assistant_message(
            session_id=session_id,
            content=llm_response,
            user_id=user_message_dto.user_id
        )
        
        return ChatResponseDTO(
            session_id=session_id,
            user_message=user_message_dto,
            assistant_message=assistant_message_dto
        )
    
    async def get_session_history(self, session_id: UUID) -> SessionChatHistory:
        """
        Получить историю сообщений по session_id
        
        Работает только с DTO
        """
        message_dtos = await self._message_repository.get_by_session_id(session_id)
        
        return SessionChatHistory(
            session_id=session_id,
            messages=[dto.to_response() for dto in message_dtos]
        )
    
    async def get_user_history(self, user_id: UUID) -> UserChatHistory:
        """
        Получить историю всех чатов пользователя.
        """
        if not await self._message_repository.user_exists(user_id):
            return UserChatHistory(user_id=user_id, sessions=[])
        
        grouped_messages = await self._message_repository.get_user_history_grouped(user_id)
        
        sessions = [
            SessionChatHistory(
                session_id=session_id,
                messages=[dto.to_response() for dto in messages]
            )
            for session_id, messages in grouped_messages.items()
        ]
        
        return UserChatHistory(
            user_id=user_id,
            sessions=sessions
        )