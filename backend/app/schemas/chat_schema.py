from datetime import datetime, timezone
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceCitation(BaseModel):
    """Cấu trúc chuẩn của một nguồn trích dẫn xác thực từ Backend."""

    model_config = ConfigDict(from_attributes=True)

    source_id: str = Field(..., min_length=1, max_length=20, description="Mã nhãn trích dẫn, ví dụ: 'S1', 'S2'")
    document_id: uuid.UUID = Field(..., description="ID của tài liệu gốc")
    filename: str = Field(..., min_length=1, max_length=255, description="Tên tệp tài liệu gốc")
    page_number: Optional[int] = Field(default=None, ge=1, description="Số trang PDF (bắt đầu từ 1)")
    chunk_index: Optional[int] = Field(default=None, ge=0, description="Thứ tự đoạn Chunk trong tài liệu")
    chunk_id: Optional[str] = Field(default=None, description="Định danh Chunk trong ChromaDB")
    excerpt: str = Field(..., min_length=1, description="Đoạn văn bản gốc dùng làm bằng chứng đối chiếu")
    score: Optional[float] = Field(default=None, description="Điểm tương đồng ngữ nghĩa Cosine")


class ChatRequest(BaseModel):
    """Schema yêu cầu hỏi đáp RAG từ người dùng."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Câu hỏi bằng ngôn ngữ tự nhiên của người dùng",
    )
    document_ids: Optional[List[uuid.UUID]] = Field(
        default=None,
        description="Danh sách ID tài liệu được chọn để tra cứu (None = tìm trên toàn bộ tài liệu đã xử lý)",
    )
    conversation_id: Optional[uuid.UUID] = Field(
        default=None,
        description="ID phiên hội thoại hiện tại (None = tự động tạo phiên mới)",
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="Số lượng đoạn văn bản Top-K cần truy xuất",
    )

    @field_validator("question")
    @classmethod
    def validate_non_empty_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Câu hỏi không được để trống hoặc chỉ chứa khoảng trắng.")
        return cleaned


class ChatResponse(BaseModel):
    """Schema phản hồi câu trả lời RAG kèm danh sách trích dẫn xác thực."""

    conversation_id: uuid.UUID = Field(..., description="ID phiên hội thoại")
    message_id: Optional[uuid.UUID] = Field(default=None, description="ID bản ghi tin nhắn trả lời")
    question: str = Field(..., description="Câu hỏi gốc của người dùng")
    answer: str = Field(..., description="Câu trả lời của AI có gắn mã [S1], [S2]")
    sources: List[SourceCitation] = Field(
        default_factory=list,
        description="Danh sách nguồn trích dẫn đã được Backend xác thực",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

