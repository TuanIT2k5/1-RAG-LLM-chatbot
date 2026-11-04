import uuid

import pytest

from app.services.citation_service import (
    CitationService,
    extract_citation_ids,
    resolve_citations_or_refuse,
    verify_citations,
)
from app.services.context_builder import build_context
from app.services.llm_service import NO_CONTEXT_REFUSAL_MESSAGE
from app.services.retriever import RetrievedChunk


def test_sp4_03_1_regex_extracts_single_and_grouped_source_ids() -> None:
    """
    [SP4-03.1] Kiểm tra bộ phân tích Regex trích xuất chính xác các mã nguồn [S1], [S3],
    hỗ trợ cả dạng viết gộp [S1, S2] hoặc chữ thường [s4], giữ đúng thứ tự xuất hiện và khử trùng lặp.
    """
    sample_answer = (
        "Người lao động được nghỉ phép 12 ngày [S1]. Đối với công việc nặng nhọc "
        "thì được nghỉ 14-16 ngày [S3, s2] và hưởng nguyên lương [S1]."
    )
    ids = extract_citation_ids(sample_answer)
    assert ids == ["S1", "S3", "S2"]
    assert extract_citation_ids("Câu trả lời không có nhãn trích dẫn nào.") == []


def test_sp4_03_2_and_3_strips_hallucinated_citations_and_maps_real_metadata() -> None:
    """
    [SP4-03.2 & SP4-03.3] Kiểm tra đối chiếu với bảng source_map của Backend:
    - Tự động loại bỏ mọi mã nguồn ảo giác không tồn tại (ví dụ [S9], [S99]) khỏi cả câu trả lời và mảng sources.
    - Tạo danh sách SourceCitation đầy đủ: source_id, document_id, filename, page_number, chunk_index và excerpt.
    """
    doc1_id = uuid.uuid4()
    doc2_id = uuid.uuid4()

    chunks = [
        RetrievedChunk(
            chunk_id=f"{doc1_id}_c0",
            text="Điều 113. Người lao động làm đủ 12 tháng được nghỉ hằng năm 12 ngày phép.",
            document_id=str(doc1_id),
            filename="Bo_luat_Lao_dong_2019.pdf",
            similarity_score=0.93,
            distance=0.07,
            page_number=45,
            chunk_index=12,
            source_type="pdf",
        ),
        RetrievedChunk(
            chunk_id=f"{doc2_id}_c1",
            text="Mục 3. Thời gian thử việc đối với vị trí đại học tối đa là 60 ngày.",
            document_id=str(doc2_id),
            filename="Quy_che_nhan_su.docx",
            similarity_score=0.88,
            distance=0.12,
            page_number=None,
            paragraph_index=5,
            chunk_index=4,
            source_type="docx",
        ),
    ]
    built = build_context(chunks)

    # Giả lập LLM trả lời có gắn [S1], [S2] hợp lệ nhưng tự bịa thêm [S9] và [S99]
    raw_llm_answer = (
        "Người lao động làm đủ 12 tháng được nghỉ 12 ngày phép [S1] [S9]. "
        "Thời gian thử việc tối đa là 60 ngày [S2, S99]."
    )

    result = verify_citations(raw_llm_answer, built.source_map)

    # 1. Các mã ảo giác S9, S99 phải bị loại bỏ hoàn toàn
    assert result.valid_source_ids == ["S1", "S2"]
    assert result.removed_source_ids == ["S9", "S99"]
    assert "[S9]" not in result.answer
    assert "[S99]" not in result.answer
    assert "[S1]" in result.answer
    assert "[S2]" in result.answer

    # 2. Kiểm tra danh sách đối tượng nguồn SourceCitation trả về cho Frontend ([SP4-03.3])
    assert len(result.sources) == 2

    s1 = result.sources[0]
    assert s1.source_id == "S1"
    assert s1.document_id == doc1_id
    assert s1.filename == "Bo_luat_Lao_dong_2019.pdf"
    assert s1.page_number == 45
    assert s1.chunk_index == 12
    assert "12 ngày phép" in s1.excerpt
    assert s1.score == pytest.approx(0.93)

    s2 = result.sources[1]
    assert s2.source_id == "S2"
    assert s2.document_id == doc2_id
    assert s2.filename == "Quy_che_nhan_su.docx"
    assert s2.page_number is None
    assert s2.chunk_index == 4
    assert "60 ngày" in s2.excerpt


def test_sp4_03_4_no_context_returns_polite_refusal_and_empty_sources_without_llm() -> None:
    """
    [SP4-03.4 & TC-07] Kiểm tra trường hợp câu hỏi không tìm thấy ngữ cảnh phù hợp:
    - Trả về câu thông báo lịch sự chuẩn và mảng sources rỗng [] mà không tốn lượt gọi LLM.
    - Nếu LLM tự trả về câu từ chối nhưng lỡ gắn kèm [S1], hệ thống cũng xóa [S1] và trả về sources rỗng.
    """
    # 1. Kiểm tra fast-path trước khi gọi LLM khi danh sách chunks rỗng
    fast_refusal = resolve_citations_or_refuse([])
    assert fast_refusal is not None
    assert fast_refusal.skipped_llm is True
    assert fast_refusal.answer == NO_CONTEXT_REFUSAL_MESSAGE
    assert fast_refusal.sources == []

    # 2. Kiểm tra verify_citations khi source_map rỗng
    empty_map_res = verify_citations("Bất kỳ câu trả lời nào [S1]", {})
    assert empty_map_res.skipped_llm is True
    assert empty_map_res.answer == NO_CONTEXT_REFUSAL_MESSAGE
    assert empty_map_res.sources == []

    # 3. Kiểm tra khi LLM trả lời từ chối nhưng vô tình gắn nhãn [S1]
    doc_id = uuid.uuid4()
    service = CitationService()
    refusal_with_tag = f"{NO_CONTEXT_REFUSAL_MESSAGE} [S1]"
    res = service.verify_and_map(
        answer_text=refusal_with_tag,
        source_map={
            "S1": {
                "source_id": "S1",
                "document_id": doc_id,
                "filename": "Doc.pdf",
                "page_number": 1,
                "chunk_index": 0,
                "excerpt": "Đoạn văn mẫu",
            }
        },
    )
    assert "[S1]" not in res.answer
    assert res.sources == []

