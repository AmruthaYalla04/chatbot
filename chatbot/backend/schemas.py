from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageBase(BaseModel):
    sender: str
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    thread_id: int
    created_at: datetime

    class Config:
        orm_mode: True

class ChatThreadBase(BaseModel):
    title: str
    user_id: int

class ChatThreadCreate(ChatThreadBase):
    pass

class ChatThread(ChatThreadBase):
    id: int
    is_deleted: bool = False
    created_at: datetime
    messages: List[Message] = []

    class Config:
        orm_mode: True

class ChatRequest(BaseModel):
    user_id: int
    message: str
    update_title: Optional[bool] = False
    suggested_title: Optional[str] = None
    model: str = "openai"  # Default to OpenAI,can be "openai" or "gemini"

class ChatResponse(BaseModel):
    user_id: int
    bot_reply: str
    chat_history: List[dict]

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    username: str
    threads: List[ChatThread] = []

    class Config:
        orm_mode: True
