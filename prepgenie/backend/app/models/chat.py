from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
import uuid

class MessageRole(enum.Enum):
    user = "user"
    assistant = "assistant"

class ConversationStatus(enum.Enum):
    active = "active"
    archived = "archived"
    exported = "exported"

class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=True)  # Auto-detected or user-defined topic
    summary = Column(Text, nullable=True)  # Auto-generated conversation summary
    status = Column(Enum(ConversationStatus), default=ConversationStatus.active)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_pinned = Column(Boolean, default=False)
    tags = Column(String(500), nullable=True)  # Comma-separated tags for filtering

    # Relationships
    user = relationship("User")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    tokens_used = Column(Integer, nullable=True)  # For usage tracking
    context_window = Column(Text, nullable=True)  # Context used for this message

    # Relationships
    user = relationship("User")
    conversation = relationship("ChatConversation", back_populates="messages")
