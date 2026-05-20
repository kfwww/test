from uuid import UUID
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

from infrastructure.utils import utc_now, generate_uuid


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    id: UUID = field(default_factory=generate_uuid)
    session_id: UUID = field(default_factory=generate_uuid)
    user_id: UUID | None = None
    role: MessageRole = MessageRole.USER
    content: str = ""
    created_at: datetime = field(default_factory=utc_now)

    @classmethod
    def create_user_message(cls, session_id: UUID, content: str) -> "Message":
        return cls(
            session_id=session_id,
            role=MessageRole.USER,
            content=content
        )
    
    @classmethod
    def create_assistant_message(cls, session_id: UUID, content: str) -> "Message":
        return cls(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content
        )