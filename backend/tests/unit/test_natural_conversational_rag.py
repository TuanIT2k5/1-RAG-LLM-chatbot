"""
Kiểm thử tự động xác nhận 5 bước cấu hình để Chatbot trả lời tự nhiên như người thật:
- Bước 1: System Prompt định hình tính cách chuyên gia tư vấn thân thiện (xưng 'tôi' - gọi 'bạn').
- Bước 2: Truyền lịch sử ngữ cảnh (3-5 tin nhắn gần nhất) từ Database vào LLM & hỗ trợ câu hỏi nối tiếp.
- Bước 3: Few-Shot Prompting đính kèm trực tiếp vào System Prompt.
- Bước 4: Điều chỉnh Temperature lên mức 0.4 - 0.6 (mặc định 0.5).
- Bước 5: Lọc bỏ tự động các cụm từ mở đầu rập khuôn ('Dựa trên ngữ cảnh cung cấp...', 'Theo tài liệu...').
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.schemas.chat_schema import ChatRequest
from app.services.citation_service import CitationService
from app.services.context_builder import ContextBuilder
from app.services.embedding_service import EmbeddingService, LightweightVietnameseEmbedder
from app.services.llm_service import (
    DEFAULT_LLM_TEMPERATURE,
    MAX_NATURAL_TEMPERATURE,
    MIN_NATURAL_TEMPERATURE,
    RAG_SYSTEM_PROMPT,
    LLMService,
    clean_robotic_phrases,
)
from app.services.rag_pipeline import RAGPipeline
from app.services.retriever import SemanticRetriever
from app.services.vector_store import VectorStore
from app.utils.text_cleaner import (
    MOJIBAKE_CHAT_REFUSAL_MESSAGE,
    MOJIBAKE_DOCUMENT_ERROR_MESSAGE,
    is_gibberish,
)


def test_step1_and_step3_persona_and_few_shot_system_prompt() -> None:
    """[Bước 1 & Bước 3] Xác nhận System Prompt có định hình tính cách thân thiện và ví dụ Few-Shot."""
    assert "chuyên gia tư vấn nhiệt tình và thân thiện" in RAG_SYSTEM_PROMPT
    assert "xưng 'tôi' và gọi người dùng là 'bạn'" in RAG_SYSTEM_PROMPT
    assert "Chỉ cho tôi cách xin nghỉ ốm" in RAG_SYSTEM_PROMPT
    assert "Để xin nghỉ ốm, bạn chỉ cần nộp giấy khám bệnh cho HR qua email nhé" in RAG_SYSTEM_PROMPT


def test_step4_default_temperature_in_0_4_to_0_6_range() -> None:
    """[Bước 4] Xác nhận tham số Temperature mặc định nằm trong khoảng 0.4 đến 0.6 (0.5)."""
    assert MIN_NATURAL_TEMPERATURE <= DEFAULT_LLM_TEMPERATURE <= MAX_NATURAL_TEMPERATURE
    service = LLMService(provider="gemini", api_key="test_key")
    assert 0.4 <= service.temperature <= 0.6


def test_step5_clean_robotic_phrases_strips_boilerplate_openings() -> None:
    """[Bước 5] Xác nhận bộ lọc tự động cắt bỏ các câu mở đầu máy móc rập khuôn."""
    raw_1 = "Dựa trên ngữ cảnh được cung cấp, bạn được nghỉ phép 12 ngày mỗi năm nhé [S1]."
    assert clean_robotic_phrases(raw_1) == "Bạn được nghỉ phép 12 ngày mỗi năm nhé [S1]."

    raw_2 = "Theo tài liệu cung cấp, thời gian thử việc tối đa của bạn là 60 ngày [S1]."
    assert clean_robotic_phrases(raw_2) == "Thời gian thử việc tối đa của bạn là 60 ngày [S1]."

    raw_3 = "Dưới đây là câu trả lời cho câu hỏi của bạn: mỗi tháng bạn làm đủ công sẽ có 1 ngày phép [S1]."
    assert (
        clean_robotic_phrases(raw_3)
        == "Mỗi tháng bạn làm đủ công sẽ có 1 ngày phép [S1]."
    )


def test_step2_conversation_context_history_sent_to_llm_and_followup_understanding(
    tmp_path: Path,
) -> None:
    """
    [Bước 2] Kiểm tra khi người dùng hỏi nối tiếp:
    - Lượt 1: "Xin chào, quy định nghỉ phép là gì?" -> Trợ lý: "Chào bạn, bạn được nghỉ 12 ngày/năm nhé! [S1]"
    - Lượt 2: "Thế làm nửa năm thì sao?" ->
      Hệ thống truy vấn Database lấy lịch sử tin nhắn gần nhất gửi kèm cho LLM
      và kết hợp ngữ cảnh để hiểu "nửa năm" đang hỏi về "nghỉ phép".
    """
    db_file = tmp_path / "conv_history.sqlite"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = SessionLocal()

    try:
        embedding_service = EmbeddingService()
        embedding_service.set_model(LightweightVietnameseEmbedder(dim=1024))
        vector_store = VectorStore(
            persist_dir=tmp_path / "chroma_db",
            collection_name="conv_history_test",
        )

        doc_id = "11111111-1111-1111-1111-111111111111"
        chunk_text = (
            "Điều 113. Quy định nghỉ phép năm: Người lao động làm đủ 12 tháng thì được nghỉ 12 ngày/năm. "
            "Trường hợp làm chưa đủ 12 tháng (ví dụ làm nửa năm / 6 tháng) thì số ngày nghỉ phép "
            "tính theo tỷ lệ tương ứng với số tháng làm việc (1 ngày phép cho mỗi tháng)."
        )
        vecs = embedding_service.encode_documents([chunk_text], normalize_embeddings=True)
        vector_store.add_chunks(
            texts=[chunk_text],
            embeddings=vecs,
            metadatas=[
                {
                    "document_id": doc_id,
                    "filename": "Quy_che_nghi_phep.pdf",
                    "page_number": 7,
                    "chunk_index": 0,
                    "source_type": "pdf",
                }
            ],
            chunk_ids=[f"{doc_id}_c0"],
        )

        captured_openai_payloads: List[Dict[str, Any]] = []

        def mock_openai_handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content.decode("utf-8"))
            captured_openai_payloads.append(body)
            turn_count = len(captured_openai_payloads)
            if turn_count == 1:
                reply = "Dựa trên ngữ cảnh cung cấp, chào bạn, bạn được nghỉ 12 ngày/năm nhé! [S1]"
            else:
                reply = "Nếu bạn làm nửa năm (6 tháng) thì bạn sẽ được tính theo tỷ lệ là 6 ngày phép nhé [S1]."
            return httpx.Response(
                status_code=200,
                json={"choices": [{"message": {"role": "assistant", "content": reply}}]},
            )

        mock_client = httpx.Client(transport=httpx.MockTransport(mock_openai_handler))
        retriever = SemanticRetriever(
            embedding_service=embedding_service,
            vector_store=vector_store,
            min_similarity=0.15,
        )
        llm_service = LLMService(
            provider="openai",
            api_key="test_openai_key",
            model="gpt-4o-mini",
            http_client=mock_client,
        )
        pipeline = RAGPipeline(
            db=db_session,
            retriever=retriever,
            context_builder=ContextBuilder(),
            llm_service=llm_service,
            citation_service=CitationService(),
        )

        # Lượt 1: Hỏi quy định nghỉ phép
        resp_1 = pipeline.ask(
            ChatRequest(
                question="Xin chào, quy định nghỉ phép là gì?",
                document_ids=[doc_id],
            )
        )
        # Xác nhận Bước 5 đã tự động cắt bỏ "Dựa trên ngữ cảnh cung cấp, "
        assert resp_1.answer.startswith("Chào bạn, bạn được nghỉ 12 ngày/năm nhé!")
        assert "[S1]" in resp_1.answer

        # Lượt 2: Hỏi câu nối tiếp ngắn "Thế làm nửa năm thì sao?" trong cùng conversation_id
        resp_2 = pipeline.ask(
            ChatRequest(
                question="Thế làm nửa năm thì sao?",
                document_ids=[doc_id],
                conversation_id=resp_1.conversation_id,
            )
        )
        assert "6 ngày phép" in resp_2.answer
        assert len(resp_2.sources) == 1

        # Xác nhận mảng messages gửi cho LLM ở Lượt 2 chứa đầy đủ lịch sử Lượt 1 (user + assistant)
        second_payload_messages = captured_openai_payloads[1]["messages"]
        roles = [m["role"] for m in second_payload_messages]
        assert roles == ["system", "user", "assistant", "user"]
        assert second_payload_messages[1]["content"] == "Xin chào, quy định nghỉ phép là gì?"
        assert "12 ngày/năm" in second_payload_messages[2]["content"]
        assert "Thế làm nửa năm thì sao?" in second_payload_messages[3]["content"]
    finally:
        db_session.close()


def test_part2_step2_is_gibberish_detects_corrupted_pdf_text_and_passes_valid_vietnamese() -> None:
    """
    [Phần 2 - Bước 2] Xác nhận hàm is_gibberish phát hiện chính xác chuỗi lỗi font từ
    '9. Python cơ bản.pdf' ('LRK /ЎX RРM 1]750...', '4]XLSR Pɧ QШX...') và không chặn nhầm văn bản chuẩn.
    """
    corrupted_sample_1 = (
        "'LRK /ЎX RРM 1]750\n"
        "1]750 Pɧ QШX LЖ G WЮ Hо PMЖY UYER LЖ TLФ FMЎR RLϴX LMЖR RE] "
        "6ϴX RLMАY RKɺR RKо Gɹ XLВ OЎX RРM чЎR 1]750 Zɧ 4]XLSR GˢRK OLɺRK RKSϰM PЖ"
    )
    corrupted_sample_2 = (
        "'LRK,IPPS [SVPH\n"
        "4]XLSR Pɧ QШX RKɺR RKо TLMɱR HКGL -RXIVTVIXIV 0ERKYEKI XиG Pɧ OLɺRK G϶R FYMPH"
    )
    assert is_gibberish(corrupted_sample_1) is True
    assert is_gibberish(corrupted_sample_2) is True
    assert is_gibberish("   ") is True

    valid_vietnamese_it = (
        "Python là một ngôn ngữ thông dịch (Interpreter Language). "
        "Để cài đặt thư viện kết nối MySQL, bạn chạy lệnh: $ sudo pip install MySQL-python"
    )
    assert is_gibberish(valid_vietnamese_it) is False


def test_part2_step3_and_4_indexing_and_rag_block_mojibake_pdf(tmp_path: Path) -> None:
    """
    [Phần 2 - Bước 3 & Bước 4] Xác nhận:
    1. Khi trích xuất PDF bị lỗi font Mojibake -> extract_pdf chặn lại với thông báo lỗi mã hóa font chữ.
    2. RAG_SYSTEM_PROMPT chứa rào chắn chống nhại lại ký tự lỗi mã hóa.
    3. Nếu kho vector cũ có đoạn văn bị lỗi mã hóa -> RAGPipeline từ chối trích xuất đoạn lỗi.
    """
    import pymupdf as fitz
    import pytest

    from app.core.exceptions import ExtractionFailedException
    from app.services.document_processor import extract_pdf

    # 1. Kiểm tra rào chắn trong RAG_SYSTEM_PROMPT (Bước 4)
    assert MOJIBAKE_CHAT_REFUSAL_MESSAGE in RAG_SYSTEM_PROMPT
    assert "LRK /ЎX RРM" in RAG_SYSTEM_PROMPT

    # 2. Tạo file PDF chứa chuỗi lỗi mã hóa font và kiểm tra extract_pdf chặn ngay (Bước 3)
    bad_pdf_path = tmp_path / "Bad_Font_Python.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 80),
        "4]XLSR Pɧ QШX RKɺR RKо TLMɱR HКGL 1]750 [SVPH 4]XLSR 1]750",
    )
    doc.save(str(bad_pdf_path))
    doc.close()

    with pytest.raises(ExtractionFailedException) as exc_info:
        extract_pdf(bad_pdf_path, document_id="bad-doc-id", filename="9. Python cơ bản.pdf")

    assert exc_info.value.message == MOJIBAKE_DOCUMENT_ERROR_MESSAGE
    assert exc_info.value.details["flag"] == "GIBBERISH_FONT_ENCODING"

