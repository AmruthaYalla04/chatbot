from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import datetime

class LoginMethod(enum.Enum):
    GOOGLE = "google"
    EMAIL = "email"
    GUEST = "guest"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    username = Column(String(255))
    hashed_password = Column(String(255), nullable=True)
    login_method = Column(String(255), default=LoginMethod.EMAIL.value)
    
    # Relationship with ChatThread
    threads = relationship("ChatThread", back_populates="user")

class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    is_deleted = Column(Boolean, default=False, nullable=False)  # Make sure this exists
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("chat_threads.id"))
    sender = Column(String(255))  # 'user' or 'assistant'
    role = Column(String(255), nullable=True)  # For compatibility
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    model = Column(String(50), nullable=True)  # Add field to store which model generated the response
    
    # Relationship
    thread = relationship("ChatThread", back_populates="messages")
