import uuid

import pytest

from app.services.context_builder import (
    ContextBuilder,
    build_context,
    format_context_block,
    format_location_label,
)
from app.services.retriever import RetrievedChunk


def test_sp4_01_1_and_2_sequential_labels_and_formatted_blocks() -> None:
    """
    [SP4-01.1 & SP4-01.2] Kiểm tra gán nhãn tuần tự [S1], [S2], [S3]... và
    định dạng khối ngữ cảnh chuẩn gồm Mã nguồn [Sx], Tên tài liệu, Số trang/Vị trí đoạn và Nội dung.
    """
    doc_pdf_id = str(uuid.uuid4())
    doc_docx_id = str(uuid.uuid4())

    chunks = [
        RetrievedChunk(
            chunk_id=f"{doc_pdf_id}_chunk_0",
            text="Điều 113. Người lao động làm việc đủ 12 tháng thì được nghỉ hằng năm 12 ngày phép.",
            document_id=doc_pdf_id,
            filename="Bo_luat_Lao_dong_2019.pdf",
            similarity_score=0.92,
            distance=0.08,
            page_number=45,
            chunk_index=12,
            source_type="pdf",
        ),
        RetrievedChunk(
            chunk_id=f"{doc_docx_id}_chunk_1",
            text="Nhân viên cần gửi đơn xin nghỉ phép trước ít nhất 03 ngày làm việc.",
            document_id=doc_docx_id,
            filename="Noi_quy_cong_ty.docx",
            similarity_score=0.84,
            distance=0.16,
            page_number=None,
            paragraph_index=8,
            section_title="Chương 2: Quy trình nghỉ phép",
            chunk_index=3,
            source_type="docx",
        ),
    ]

    built = build_context(chunks)

    # [SP4-01.1] Nhãn nguồn được gán tuần tự S1, S2
    assert list(built.source_map.keys()) == ["S1", "S2"]
    assert built.included_count == 2
    assert built.omitted_count == 0

    # [SP4-01.2] Kiểm tra định dạng rõ ràng từng khối ngữ cảnh
    assert "[S1] Tài liệu: Bo_luat_Lao_dong_2019.pdf | Vị trí: Trang 45 | Đoạn #12" in built.context_text
    assert "Điều 113. Người lao động làm việc đủ 12 tháng" in built.context_text

    assert (
        "[S2] Tài liệu: Noi_quy_cong_ty.docx | Vị trí: Mục: Chương 2: Quy trình nghỉ phép | Đoạn #8"
        in built.context_text
    )
    assert "Nhân viên cần gửi đơn xin nghỉ phép trước ít nhất 03 ngày" in built.context_text


def test_sp4_01_3_source_map_stores_complete_authentic_metadata() -> None:
    """
    [SP4-01.3] Kiểm tra bảng ánh xạ source_map lưu đầy đủ metadata thật của Chunk
    và hỗ trợ chuyển đổi sang SourceCitation phục vụ xác thực hai lớp.
    """
    doc_id = uuid.uuid4()
    chunk = RetrievedChunk(
        chunk_id=f"{doc_id}_chunk_5",
        text="Thời gian thử việc không quá 60 ngày đối với trình độ đại học.",
        document_id=str(doc_id),
        filename="Quy_che_tuyen_dung.pdf",
        similarity_score=0.89,
        distance=0.11,
        page_number=14,
        chunk_index=5,
        source_type="pdf",
    )

    context_text, source_map = build_context([chunk])
    assert "[S1]" in context_text
    assert "S1" in source_map

    entry = source_map["S1"]
    assert entry.source_id == "S1"
    assert entry.label == "[S1]"
    assert entry.document_id == str(doc_id)
    assert entry.filename == "Quy_che_tuyen_dung.pdf"
    assert entry.page_number == 14
    assert entry.chunk_index == 5
    assert entry.chunk_id == f"{doc_id}_chunk_5"
    assert entry.score == pytest.approx(0.89)
    assert "60 ngày" in entry.excerpt

    # Kiểm tra chuyển đổi sang Pydantic SourceCitation
    citation = entry.to_source_citation()
    assert citation.source_id == "S1"
    assert citation.document_id == doc_id
    assert citation.filename == "Quy_che_tuyen_dung.pdf"
    assert citation.page_number == 14
    assert citation.chunk_index == 5
    assert citation.score == pytest.approx(0.89)


def test_sp4_01_4_context_window_token_and_char_budget_enforcement() -> None:
    """
    [SP4-01.4] Kiểm soát tổng độ dài chuỗi Context để đảm bảo không vượt quá
    giới hạn cửa sổ ngữ cảnh (Context Window) của mô hình LLM.
    """
    doc_id = str(uuid.uuid4())
    long_chunks = [
        {
            "chunk_id": f"{doc_id}_c{i}",
            "document_id": doc_id,
            "filename": "Tai_lieu_dai.pdf",
            "page_number": i + 1,
            "chunk_index": i,
            "similarity_score": 0.95 - (i * 0.05),
            "text": " ".join(
                [f"Nội dung điều khoản số {i + 1} quy định chi tiết quyền lợi bảo hiểm"] * 12
            ),
        }
        for i in range(5)
    ]

    # Đặt giới hạn cửa sổ ngữ cảnh nhỏ (max_context_tokens = 180)
    builder = ContextBuilder(max_context_tokens=180)
    built = builder.build(long_chunks)

    assert built.total_tokens <= 180
    assert built.included_count >= 1
    assert built.omitted_count >= 1
    assert built.included_count + built.omitted_count == 5
    # Chỉ các đoạn được đưa vào Context mới có mặt trong source_map
    assert len(built.source_map) == built.included_count


def test_context_builder_handles_empty_input_and_invalid_limits() -> None:
    """Kiểm tra xử lý danh sách rỗng và kiểm tra tham số khởi tạo không hợp lệ."""
    empty_built = build_context([])
    assert empty_built.context_text == ""
    assert empty_built.source_map == {}
    assert empty_built.total_tokens == 0
    assert empty_built.included_count == 0

    assert format_location_label() == "Không rõ vị trí"
    block = format_context_block(
        source_id="[S1]",
        filename="test.pdf",
        text="Nội dung thử nghiệm",
        page_number=2,
    )
    assert block.startswith("[S1] Tài liệu: test.pdf | Vị trí: Trang 2")

    with pytest.raises(ValueError):
        ContextBuilder(max_context_tokens=0)

