from pathlib import Path
from typing import Dict, List, Sequence
import uuid

from fastapi.testclient import TestClient
import httpx
import numpy as np
import pymupdf as fitz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_document_service, get_rag_pipeline
from app.database.connection import Base
from app.main import app
from app.services.citation_service import CitationService
from app.services.context_builder import ContextBuilder
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import NO_CONTEXT_REFUSAL_MESSAGE, LLMService
from app.services.rag_pipeline import RAGPipeline
from app.services.retriever import SemanticRetriever
from app.services.vector_store import VectorStore


class SemanticTestEmbeddingModel:
    """
    Mô hình embedding ngữ nghĩa 1024 chiều cho kiểm thử tích hợp end-to-end RAG API:
    - Trục 0: Chủ đề nghỉ phép năm / 12 ngày phép (Trang 2)
    - Trục 1: Chủ đề thử việc / 60 ngày (Trang 1)
    - Trục 50: Câu hỏi ngoài phạm vi tài liệu (ví dụ dự báo thời tiết, giá cổ phiếu) ->
      vector trực giao (cosine similarity = 0.0 < threshold 0.35) nên Retriever trả về [].
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _encode_one(self, text: str) -> np.ndarray:
        lower = text.lower()
        vec = np.zeros(self.dim, dtype=np.float32)

        if any(k in lower for k in ["nghỉ phép", "nghỉ hằng năm", "12 ngày", "phép năm"]):
            vec[0] = 10.0
        elif any(k in lower for k in ["thử việc", "60 ngày", "tập sự"]):
            vec[1] = 10.0
        else:
            # Chủ đề ngoài tài liệu hoàn toàn trực giao với trục 0 và trục 1
            vec[50] = 10.0

        norm = np.linalg.norm(vec)
        return vec / (norm if norm > 0 else 1.0)

    def encode(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        return np.vstack([self._encode_one(t) for t in texts])


def _build_hr_policy_pdf_bytes() -> bytes:
    """Tạo tệp PDF 2 trang quy định nhân sự để kiểm thử trích dẫn chính xác page_number."""
    doc = fitz.open()
    pages = [
        (
            1,
            "QUY CHẾ TUYỂN DỤNG CÔNG TY\n\n"
            "Điều 1. Thời gian thử việc đối với vị trí yêu cầu trình độ đại học là tối đa 60 ngày.",
        ),
        (
            2,
            "QUY CHẾ NGHỈ PHÉP NĂM\n\n"
            "Điều 5. Người lao động làm việc đủ 12 tháng thì được nghỉ hằng năm 12 ngày phép hưởng nguyên lương.",
        ),
    ]
    for page_no, content in pages:
        page = doc.new_page(width=595, height=842)
        writer = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")
        writer.append((50, 70), f"Quy che nhan su - Trang {page_no}", font=font, fontsize=12)
        y = 110
        for line in content.split("\n"):
            writer.append((50, y), line, font=font, fontsize=11)
            y += 20
        writer.write_text(page)

    data = doc.tobytes()
    doc.close()
    return data


def test_sp4_05_and_sprint4_dod_full_rag_chat_and_history_apis(
    tmp_path: Path,
) -> None:
    """
    [SP4-05.1 -> SP4-05.4 & Sprint 4 DoD] Kiểm thử tích hợp toàn diện:
    1. Tải tệp PDF lên qua POST /api/documents/upload.
    2. Gửi câu hỏi lần 1 qua POST /api/chat (không truyền conversation_id):
       - Tự động tạo phiên hội thoại mới đặt tiêu đề theo câu hỏi đầu tiên ([SP4-05.2]).
       - Trả về câu trả lời tiếng Việt tự nhiên kèm mảng 'sources' có đúng tên tệp, page_number=2 ([SP4-05.1]).
       - Loại bỏ nhãn ảo giác [S99] nếu LLM tự sinh ra.
    3. Gửi câu hỏi ngoài phạm vi tài liệu cùng conversation_id:
       - Từ chối lịch sự và trả về mảng 'sources' rỗng [] mà không tốn lượt gọi LLM ([SP4-03.4 & DoD]).
    4. Kiểm tra GET /api/conversations và GET /api/conversations/{id}/messages:
       - Đầy đủ lịch sử tin nhắn 'user' & 'assistant' và trích dẫn 'sources' từ PostgreSQL/SQL ([SP4-05.3 & SP4-05.4]).
    """
    db_file = tmp_path / "test_chat_rag.sqlite"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = SessionLocal()

    embedding_service = EmbeddingService()
    embedding_service.set_model(SemanticTestEmbeddingModel(dim=1024))
    vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
    upload_dir = tmp_path / "uploads"

    llm_call_count = 0

    def mock_gemini_handler(request: httpx.Request) -> httpx.Response:
        nonlocal llm_call_count
        llm_call_count += 1
        # Giả lập LLM trả lời đúng kèm [S1] và cố tình kèm 1 nhãn ảo giác [S99] để kiểm tra bộ lọc 2 lớp
        return httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        "Theo quy định tại Điều 5, người lao động làm việc đủ 12 tháng "
                                        "được nghỉ hằng năm 12 ngày phép hưởng nguyên lương [S1] [S99]."
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    mock_http_client = httpx.Client(transport=httpx.MockTransport(mock_gemini_handler))

    def override_get_document_service() -> DocumentService:
        return DocumentService(
            db=db_session,
            embedding_service=embedding_service,
            vector_store=vector_store,
            default_upload_dir=upload_dir,
        )

    def override_get_rag_pipeline() -> RAGPipeline:
        retriever = SemanticRetriever(
            embedding_service=embedding_service,
            vector_store=vector_store,
            min_similarity=0.35,
        )
        llm_service = LLMService(
            provider="gemini",
            api_key="test_key",
            model="gemini-2.5-flash",
            temperature=0.1,
            http_client=mock_http_client,
        )
        return RAGPipeline(
            db=db_session,
            retriever=retriever,
            context_builder=ContextBuilder(),
            llm_service=llm_service,
            citation_service=CitationService(),
        )

    app.dependency_overrides[get_document_service] = override_get_document_service
    app.dependency_overrides[get_rag_pipeline] = override_get_rag_pipeline

    try:
        client = TestClient(app)

        # Bước 1: Tải lên tệp PDF chính sách nhân sự (2 trang)
        pdf_bytes = _build_hr_policy_pdf_bytes()
        upload_resp = client.post(
            "/api/documents/upload",
            files={"file": ("Quy_che_nghi_phep_2026.pdf", pdf_bytes, "application/pdf")},
        )
        assert upload_resp.status_code == 201
        uploaded_doc_id = upload_resp.json()["document"]["id"]

        # Bước 2: [SP4-05.1 & SP4-05.2] Đặt câu hỏi có trong tài liệu (chưa truyền conversation_id)
        question_1 = "Người lao động làm việc đủ 12 tháng được nghỉ phép năm bao nhiêu ngày?"
        chat_resp_1 = client.post(
            "/api/chat",
            json={
                "question": question_1,
                "document_ids": [uploaded_doc_id],
                "conversation_id": None,
                "top_k": 5,
            },
        )
        assert chat_resp_1.status_code == 200
        chat_data_1 = chat_resp_1.json()

        conv_id = chat_data_1["conversation_id"]
        assert conv_id is not None
        assert chat_data_1["message_id"] is not None
        assert "12 ngày phép" in chat_data_1["answer"]
        assert "[S1]" in chat_data_1["answer"]
        assert "[S99]" not in chat_data_1["answer"]  # Đã lọc sạch nhãn ảo giác [S99]
        assert llm_call_count == 1

        # Kiểm tra mảng 'sources' trả về đúng tên tệp và số trang PDF = 2
        sources_1 = chat_data_1["sources"]
        assert len(sources_1) == 1
        assert sources_1[0]["source_id"] == "S1"
        assert sources_1[0]["document_id"] == uploaded_doc_id
        assert sources_1[0]["filename"] == "Quy_che_nghi_phep_2026.pdf"
        assert sources_1[0]["page_number"] == 2
        assert "12 ngày phép" in sources_1[0]["excerpt"]

        # Bước 3: [Sprint 4 DoD & TC-07] Đặt câu hỏi ngoài phạm vi tài liệu trong cùng phiên hội thoại
        question_2 = "Dự báo thời tiết ngày mai tại Hà Nội và giá vàng thế giới là bao nhiêu?"
        chat_resp_2 = client.post(
            "/api/chat",
            json={
                "question": question_2,
                "document_ids": [uploaded_doc_id],
                "conversation_id": conv_id,
            },
        )
        assert chat_resp_2.status_code == 200
        chat_data_2 = chat_resp_2.json()

        assert chat_data_2["conversation_id"] == conv_id
        assert chat_data_2["answer"] == NO_CONTEXT_REFUSAL_MESSAGE
        assert chat_data_2["sources"] == []
        # Xác nhận không tốn thêm lượt gọi LLM khi không tìm thấy ngữ cảnh
        assert llm_call_count == 1

        # Bước 4: [SP4-05.4] Kiểm tra GET /api/conversations
        convs_resp = client.get("/api/conversations")
        assert convs_resp.status_code == 200
        convs_data = convs_resp.json()
        assert convs_data["total"] == 1
        assert convs_data["items"][0]["id"] == conv_id
        assert convs_data["items"][0]["title"] == question_1

        # Bước 5: [SP4-05.3 & SP4-05.4] Kiểm tra GET /api/conversations/{id}/messages
        history_resp = client.get(f"/api/conversations/{conv_id}/messages")
        assert history_resp.status_code == 200
        history_data = history_resp.json()

        assert history_data["conversation"]["id"] == conv_id
        messages: List[Dict] = history_data["messages"]
        # Phải có đúng 4 bản ghi tin nhắn: (User 1 -> Assistant 1 -> User 2 -> Assistant 2)
        assert len(messages) == 4
        assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
        assert messages[0]["content"] == question_1
        assert messages[0]["sources"] == []

        # Tin nhắn Assistant 1 phải lưu đầy đủ nguồn trích dẫn từ bảng 'message_sources'
        assert len(messages[1]["sources"]) == 1
        saved_source = messages[1]["sources"][0]
        assert saved_source["source_id"] == "S1"
        assert saved_source["document_id"] == uploaded_doc_id
        assert saved_source["filename"] == "Quy_che_nghi_phep_2026.pdf"
        assert saved_source["page_number"] == 2
        assert "12 ngày phép" in saved_source["excerpt"]

        # Tin nhắn Assistant 2 (ngoài tài liệu) có mảng sources rỗng
        assert messages[3]["content"] == NO_CONTEXT_REFUSAL_MESSAGE
        assert messages[3]["sources"] == []

        # Bước 6: Kiểm tra lỗi 404 khi truy vấn conversation_id không tồn tại
        unknown_conv_id = str(uuid.uuid4())
        not_found_resp = client.get(f"/api/conversations/{unknown_conv_id}/messages")
        assert not_found_resp.status_code == 404
        assert not_found_resp.json()["error_code"] == "CONVERSATION_NOT_FOUND"
    finally:
        mock_http_client.close()
        app.dependency_overrides.clear()
        db_session.close()

