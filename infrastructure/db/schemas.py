from datetime import datetime, UTC
from uuid import UUID
from typing import Optional

from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column


Base = declarative_base()


class UserORM(Base):
    """ORM модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=datetime.now(UTC), 
        nullable=False
    )
    
    messages = relationship("MessageORM", back_populates="user")


class MessageORM(Base):
    __tablename__ = "messages"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        nullable=False, 
        index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=datetime.now(UTC), 
        nullable=False
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), 
        ForeignKey("users.id"),
        nullable=True
    )
    
    user = relationship("UserORM", back_populates="messages")