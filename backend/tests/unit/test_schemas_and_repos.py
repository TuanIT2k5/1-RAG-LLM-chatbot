import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database.repositories import ConversationRepository, DocumentRepository
from app.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentStatusUpdate,
    SourceCitation,
)


def test_chat_request_and_source_citation_validation() -> None:
    """Kiểm tra Pydantic validation cho ChatRequest, SourceCitation và ChatResponse."""
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    req = ChatRequest(
        question="  Thời gian thử việc tối đa là bao lâu?  ",
        document_ids=[doc_id],
        conversation_id=conv_id,
    )
    assert req.question == "Thời gian thử việc tối đa là bao lâu?"
    assert req.document_ids == [doc_id]

    # Câu hỏi chỉ chứa khoảng trắng phải bị từ chối
    with pytest.raises(ValidationError):
        ChatRequest(question="   ")

    citation = SourceCitation(
        source_id="S1",
        document_id=doc_id,
        filename="Bo_luat_2019.pdf",
        page_number=18,
        chunk_index=4,
        excerpt="Thời gian thử việc không quá 60 ngày đối với trình độ đại học...",
        score=0.92,
    )
    resp = ChatResponse(
        conversation_id=conv_id,
        question=req.question,
        answer="Thời gian thử việc tối đa là 60 ngày [S1].",
        sources=[citation],
    )
    assert len(resp.sources) == 1
    assert resp.sources[0].source_id == "S1"
    assert resp.sources[0].page_number == 18


def test_document_repository_crud() -> None:
    """Kiểm tra thêm, truy vấn, cập nhật trạng thái và xóa trên DocumentRepository."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with TestingSession() as db:
        repo = DocumentRepository(db)

        # 1. Create
        created = repo.create(
            DocumentCreate(
                filename="Noi_quy_cong_ty.docx",
                storage_path="./storage/uploads/abc.docx",
                file_type="docx",
                file_size=512000,
                status="processing",
            )
        )
        assert created.status == "processing"
        assert repo.count_documents() == 1

        # 2. Update status -> processed
        updated = repo.update_status(
            created.id,
            DocumentStatusUpdate(status="processed", chunk_count=18),
        )
        assert updated is not None
        assert updated.status == "processed"
        assert updated.chunk_count == 18

        schema_obj = DocumentResponse.model_validate(updated)
        assert schema_obj.filename == "Noi_quy_cong_ty.docx"

        # 3. List & Get by IDs
        docs = repo.list_documents(status="processed")
        assert len(docs) == 1
        assert len(repo.get_by_ids([created.id])) == 1

        # 4. Delete
        assert repo.delete(created.id) is True
        assert repo.get_by_id(created.id) is None
        assert repo.count_documents() == 0


def test_conversation_repository_crud() -> None:
    """Kiểm tra tạo hội thoại, thêm tin nhắn kèm trích dẫn và truy vấn lịch sử."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with TestingSession() as db:
        doc_repo = DocumentRepository(db)
        conv_repo = ConversationRepository(db)

        doc = doc_repo.create(
            DocumentCreate(
                filename="Quy_che_dao_tao.pdf",
                storage_path="./storage/uploads/quyche.pdf",
                file_type="pdf",
                file_size=1024000,
                status="processed",
            )
        )

        # Tạo phiên hội thoại
        conv = conv_repo.create_conversation(title="Hỏi đáp quy chế đào tạo")
        assert conv_repo.count_conversations() == 1

        # Thêm tin nhắn user
        conv_repo.add_message(
            conversation_id=conv.id,
            role="user",
            content="Điều kiện tốt nghiệp loại giỏi là gì?",
        )

        # Thêm tin nhắn assistant kèm trích dẫn SourceCitation
        citation = SourceCitation(
            source_id="S1",
            document_id=doc.id,
            filename=doc.filename,
            page_number=12,
            chunk_index=3,
            chunk_id=f"{doc.id}_chunk_3",
            excerpt="Sinh viên đạt GPA từ 3.20 đến 3.59 được xếp loại Giỏi.",
            score=0.89,
        )
        conv_repo.add_message(
            conversation_id=conv.id,
            role="assistant",
            content="GPA từ 3.20 đến 3.59 đạt loại Giỏi [S1].",
            citations=[citation],
        )

        messages = conv_repo.get_messages_by_conversation(conv.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert len(messages[1].sources) == 1
        assert messages[1].sources[0].source_label == "S1"
        assert messages[1].sources[0].page_number == 12
        assert messages[1].sources[0].document.filename == "Quy_che_dao_tao.pdf"

        # Xóa hội thoại
        assert conv_repo.delete_conversation(conv.id) is True
        assert conv_repo.count_conversations() == 0

