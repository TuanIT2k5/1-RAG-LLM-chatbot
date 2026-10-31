from datetime import datetime
from typing import List, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat_schema import SourceCitation


class ConversationCreate(BaseModel):
    """Schema đầu vào để tạo một phiên hội thoại mới."""

    title: str = Field(
        default="Cuộc trò chuyện mới",
        min_length=1,
        max_length=255,
        description="Tiêu đề phiên hội thoại",
    )
    user_id: Optional[uuid.UUID] = None


class ConversationResponse(BaseModel):
    """Schema thông tin một phiên hội thoại."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    created_at: datetime


class ConversationListResponse(BaseModel):
    """Schema trả về danh sách các phiên hội thoại."""

    total: int = Field(..., ge=0)
    items: List[ConversationResponse] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """Schema thông tin một tin nhắn trong lịch sử hội thoại kèm nguồn trích dẫn."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    sources: List[SourceCitation] = Field(default_factory=list)
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    """Schema trả về chi tiết phiên hội thoại và toàn bộ lịch sử tin nhắn."""

    conversation: ConversationResponse
    messages: List[MessageResponse] = Field(default_factory=list)

