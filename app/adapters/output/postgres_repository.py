import asyncio
from uuid import UUID
from collections import defaultdict

from sqlalchemy import Column, DateTime, String, ForeignKey, select, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from ...core.ports.dto import MessageRole
from infrastructure.config.settings import settings
from app.core.ports.output.message_repository import MessageRepository
from app.core.ports.dto import MessageDTO
from infrastructure.utils import utc_now, generate_uuid

Base = declarative_base()


class UserORM(Base):
    __tablename__ = "users"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    messages = relationship("MessageORM", back_populates="user")


class MessageORM(Base):
    __tablename__ = "messages"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    session_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    user = relationship("UserORM", back_populates="messages")
    
    def to_dto(self) -> MessageDTO:
        """Конвертация ORM модели в DTO"""
        return MessageDTO(
            id=self.id,
            session_id=self.session_id,
            role=MessageRole(self.role),
            content=self.content,
            created_at=self.created_at,
            user_id=self.user_id
        )
    
    @classmethod
    def from_dto(cls, dto: MessageDTO) -> "MessageORM":
        """Создание ORM модели из DTO"""
        return cls(
            id=dto.id,
            session_id=dto.session_id,
            role=dto.role.value,
            content=dto.content,
            created_at=dto.created_at,
            user_id=dto.user_id
        )


class PostgresMessageRepository(MessageRepository):
    """Адаптер репозитория - конвертирует между DTO и ORM моделями"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "timeout": 10,
                "command_timeout": 30
            }
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def initialize(self):
        """Создать таблицы в БД если их нет"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    
    async def _ensure_user_exists(self, user_id: UUID) -> None:
        """Внутренний метод для создания пользователя если его нет"""
        if not await self.user_exists(user_id):
            async with self.async_session() as session:
                async with session.begin():
                    user = UserORM(id=user_id)
                    session.add(user)
    
    async def save_user_message(self, session_id: UUID, content: str, user_id: UUID | None = None) -> MessageDTO:
        """Сохранить сообщение пользователя и вернуть DTO"""
        if not user_id:
            user_id = generate_uuid()
        
        await self._ensure_user_exists(user_id)
        
        dto = MessageDTO.create_user_message(
            session_id=session_id,
            content=content,
            user_id=user_id
        )
        return await self._save(dto)
    
    async def save_assistant_message(self, session_id: UUID, content: str, user_id: UUID | None = None) -> MessageDTO:
        """Сохранить ответ ассистента и вернуть DTO"""
        dto = MessageDTO.create_assistant_message(
            session_id=session_id,
            content=content,
            user_id=user_id
        )
        return await self._save(dto)
    
    async def _save(self, message_dto: MessageDTO) -> MessageDTO:
        """Внутренний метод сохранения DTO в БД"""
        async with self.async_session() as session:
            async with session.begin():
                orm_message = MessageORM.from_dto(message_dto)
                session.add(orm_message)
            return message_dto
    
    async def get_by_session_id(self, session_id: UUID) -> list[MessageDTO]:
        """Получить все сообщения сессии в виде DTO"""
        async with self.async_session() as session:
            result = await session.execute(
                select(MessageORM)
                .where(MessageORM.session_id == session_id)
                .order_by(MessageORM.created_at)
            )
            orm_messages = result.scalars().all()
            return [msg.to_dto() for msg in orm_messages]
    
    async def session_exists(self, session_id: UUID) -> bool:
        """Проверить существование сессии"""
        async with self.async_session() as session:
            result = await session.execute(
                select(MessageORM)
                .where(MessageORM.session_id == session_id)
                .limit(1)
            )
            return result.first() is not None

    async def user_exists(self, user_id: UUID) -> bool:
        """Проверить существование пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserORM).where(UserORM.id == user_id)
            )
            return result.scalar_one_or_none() is not None
    
    async def is_available(self) -> bool:
        try:
            async with asyncio.timeout(3):
                async with self.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    return True
        except:
            return False
        
    async def get_user_history_grouped(self, user_id: UUID) -> dict[UUID, list[MessageDTO]]:
        """
        Получить все сообщения пользователя, сгруппированные по сессиям.
        """
        async with self.async_session() as session:
            result = await session.execute(
                select(MessageORM)
                .where(MessageORM.user_id == user_id)
                .order_by(MessageORM.session_id, MessageORM.created_at)
            )
            orm_messages = result.scalars().all()
            
            grouped = defaultdict(list)
            for msg in orm_messages:
                grouped[msg.session_id].append(msg.to_dto())
            
            return dict(grouped)

    async def close(self):
        """Закрыть соединение с БД"""
        await self.engine.dispose()