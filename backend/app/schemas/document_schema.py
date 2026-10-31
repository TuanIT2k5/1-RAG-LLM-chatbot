from datetime import datetime
from typing import List, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

DocumentStatusType = Literal["processing", "processed", "failed"]


class DocumentBase(BaseModel):
    """Thuộc tính cơ bản của tài liệu."""

    filename: str = Field(..., min_length=1, max_length=255, description="Tên tệp gốc của người dùng")
    file_type: Literal["pdf", "docx"] = Field(..., description="Định dạng tệp (pdf hoặc docx)")
    file_size: int = Field(..., ge=1, description="Kích thước tệp tính bằng byte")


class DocumentCreate(DocumentBase):
    """Schema đầu vào khi tạo bản ghi tài liệu mới trong CSDL."""

    id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    storage_path: str = Field(..., min_length=1, max_length=512, description="Đường dẫn lưu tệp vật lý")
    status: DocumentStatusType = Field(default="processing")


class DocumentStatusUpdate(BaseModel):
    """Schema cập nhật trạng thái xử lý tài liệu sau khi chạy Indexing Pipeline."""

    status: DocumentStatusType = Field(..., description="Trạng thái mới: processing | processed | failed")
    chunk_count: Optional[int] = Field(default=None, ge=0, description="Tổng số Chunk đã lập chỉ mục")
    error_message: Optional[str] = Field(default=None, description="Thông báo lỗi nếu status='failed'")


class DocumentResponse(BaseModel):
    """Schema dữ liệu tài liệu trả về cho Frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    filename: str
    storage_path: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Schema phản hồi sau khi tải tệp lên thành công."""

    message: str = Field(default="Tải lên và xử lý tài liệu thành công.")
    document: DocumentResponse


class DocumentListResponse(BaseModel):
    """Schema trả về danh sách các tài liệu đã tải lên."""

    total: int = Field(..., ge=0)
    items: List[DocumentResponse] = Field(default_factory=list)


class DocumentDeleteResponse(BaseModel):
    """Schema phản hồi khi xóa tài liệu đồng bộ."""

    message: str = Field(default="Đã xóa đồng bộ tài liệu khỏi hệ thống.")
    document_id: uuid.UUID

