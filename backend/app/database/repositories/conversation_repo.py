from typing import List, Optional, Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database.models import Conversation, Message, MessageSource
from app.schemas.chat_schema import SourceCitation


class ConversationRepository:
    """Repository quản lý các thao tác CRUD trên bảng 'conversations', 'messages' và 'message_sources'."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_conversation(
        self,
        title: str = "Cuộc trò chuyện mới",
        user_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        """Tạo phiên hội thoại mới."""
        conv = Conversation(
            id=conversation_id or uuid.uuid4(),
            user_id=user_id,
            title=title.strip() or "Cuộc trò chuyện mới",
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_conversation_by_id(
        self, conversation_id: uuid.UUID
    ) -> Optional[Conversation]:
        """Lấy thông tin phiên hội thoại theo ID."""
        return self.db.get(Conversation, conversation_id)

    def list_conversations(
        self,
        user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Conversation]:
        """Lấy danh sách các phiên hội thoại sắp xếp mới nhất lên đầu."""
        stmt = select(Conversation)
        if user_id is not None:
            stmt = stmt.where(Conversation.user_id == user_id)
        stmt = stmt.order_by(Conversation.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count_conversations(self, user_id: Optional[uuid.UUID] = None) -> int:
        """Đếm tổng số phiên hội thoại."""
        stmt = select(func.count(Conversation.id))
        if user_id is not None:
            stmt = stmt.where(Conversation.user_id == user_id)
        return int(self.db.scalar(stmt) or 0)

    def update_title(
        self,
        conversation_id: uuid.UUID,
        title: str,
    ) -> Optional[Conversation]:
        """Cập nhật tiêu đề phiên hội thoại."""
        conv = self.get_conversation_by_id(conversation_id)
        if conv is None:
            return None
        conv.title = title.strip()
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        """Xóa phiên hội thoại (cascade xóa toàn bộ tin nhắn và trích dẫn liên quan)."""
        conv = self.get_conversation_by_id(conversation_id)
        if conv is None:
            return False
        self.db.delete(conv)
        self.db.commit()
        return True

    def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: Optional[Sequence[SourceCitation]] = None,
    ) -> Message:
        """Lưu tin nhắn mới ('user' hoặc 'assistant') kèm danh sách trích dẫn nguồn nếu có."""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.db.add(msg)
        self.db.flush()

        if citations:
            for item in citations:
                source_row = MessageSource(
                    message_id=msg.id,
                    document_id=item.document_id,
                    source_label=item.source_id,
                    chunk_id=item.chunk_id or f"{item.document_id}_chunk_{item.chunk_index or 0}",
                    page_number=item.page_number,
                    chunk_index=item.chunk_index,
                    excerpt=item.excerpt,
                    score=item.score,
                )
                self.db.add(source_row)

        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_messages_by_conversation(
        self, conversation_id: uuid.UUID
    ) -> List[Message]:
        """Lấy toàn bộ lịch sử tin nhắn của một phiên hội thoại kèm nguồn trích dẫn và tài liệu."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .options(
                selectinload(Message.sources).selectinload(MessageSource.document)
            )
            .order_by(Message.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

