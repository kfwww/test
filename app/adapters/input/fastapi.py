from uuid import UUID
from fastapi import FastAPI, HTTPException, Request

from app.core.ports.dto import (
    ChatRequest,
    ChatResponse,
    SessionChatHistory,
    UserChatHistory,
    HealthResponse,
    ChatRequestDTO
)


def create_app() -> FastAPI:
    """
    Создать FastAPI приложение.
    Зависимости внедряются через app.state в lifespan.
    """
    
    app = FastAPI(title="LLM Chat API", version="1.0.0")
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check(request: Request):
        """Проверка доступности сервиса"""
        use_case = request.app.state.health_check_use_case
        return await use_case.check_health()
    
    @app.post("/chat", response_model=ChatResponse)
    async def send_message(request: ChatRequest, req: Request):
        """Отправить сообщение и получить ответ модели"""
        try:
            chat_request_dto = ChatRequestDTO.from_request(request)
            use_case = req.app.state.send_message_use_case
            response_dto = await use_case.send_message(chat_request_dto)
            return response_dto.to_response()
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/chat/{session_id}", response_model=SessionChatHistory)
    async def get_session_chat_history(session_id: UUID, request: Request):
        """Получить историю диалога по session_id"""
        try:
            use_case = request.app.state.get_history_use_case
            return await use_case.get_session_history(session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/users/{user_id}/history", response_model=UserChatHistory)
    async def get_user_chat_history(user_id: UUID, request: Request):
        """Получить историю всех чатов пользователя"""
        try:
            use_case = request.app.state.get_user_history_use_case
            return await use_case.get_user_history(user_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    return app