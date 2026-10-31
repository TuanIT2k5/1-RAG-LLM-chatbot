from typing import List, Optional, Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Document
from app.schemas.document_schema import DocumentCreate, DocumentStatusUpdate


class DocumentRepository:
    """Repository quản lý các thao tác CRUD trên bảng 'documents'."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: DocumentCreate) -> Document:
        """Thêm bản ghi tài liệu mới vào cơ sở dữ liệu."""
        doc = Document(
            id=data.id or uuid.uuid4(),
            user_id=data.user_id,
            filename=data.filename,
            storage_path=data.storage_path,
            file_type=data.file_type,
            file_size=data.file_size,
            status=data.status,
            chunk_count=0,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        """Lấy thông tin chi tiết một tài liệu theo ID."""
        return self.db.get(Document, document_id)

    def get_by_ids(self, document_ids: Sequence[uuid.UUID]) -> List[Document]:
        """Lấy danh sách các tài liệu theo mảng ID."""
        if not document_ids:
            return []
        stmt = (
            select(Document)
            .where(Document.id.in_(document_ids))
            .order_by(Document.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_documents(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        """Truy vấn danh sách tài liệu có phân trang và lọc theo trạng thái."""
        stmt = select(Document)
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Document.status == status)
        stmt = stmt.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_documents(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> int:
        """Đếm tổng số lượng tài liệu thỏa mãn điều kiện lọc."""
        stmt = select(func.count(Document.id))
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Document.status == status)
        return int(self.db.scalar(stmt) or 0)

    def update_status(
        self,
        document_id: uuid.UUID,
        update_data: DocumentStatusUpdate,
    ) -> Optional[Document]:
        """Cập nhật trạng thái xử lý (processing/processed/failed) và số lượng Chunk."""
        doc = self.get_by_id(document_id)
        if doc is None:
            return None

        doc.status = update_data.status
        if update_data.chunk_count is not None:
            doc.chunk_count = update_data.chunk_count
        if update_data.error_message is not None:
            doc.error_message = update_data.error_message

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, document_id: uuid.UUID) -> bool:
        """Xóa bản ghi tài liệu khỏi cơ sở dữ liệu (tự động cascade xóa message_sources)."""
        doc = self.get_by_id(document_id)
        if doc is None:
            return False
        self.db.delete(doc)
        self.db.commit()
        return True

