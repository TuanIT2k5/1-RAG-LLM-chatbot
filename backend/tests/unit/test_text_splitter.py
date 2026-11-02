import uuid

import pytest

from app.services.document_processor import ExtractedUnit
from app.services.text_splitter import (
    RecursiveTextSplitter,
    count_tokens,
    split_extracted_units,
)


def test_recursive_splitter_respects_chunk_size_and_overlap() -> None:
    """[SP2-05.1 & SP2-05.2] Kiểm tra độ dài mỗi Chunk <= chunk_size và có phần overlap giữa 2 Chunk."""
    sentences = [
        f"Câu số {i} quy định về quyền lợi và nghĩa vụ của người lao động tại doanh nghiệp."
        for i in range(1, 15)
    ]
    long_text = " ".join(sentences)

    splitter = RecursiveTextSplitter(chunk_size=50, chunk_overlap=15)
    chunks = splitter.split_text(long_text)

    assert len(chunks) >= 3
    for chunk in chunks:
        assert count_tokens(chunk) <= 50

    # Kiểm tra phần cuối của Chunk 0 xuất hiện ở đầu Chunk 1 (overlap)
    tail_words_chunk0 = chunks[0].split()[-5:]
    overlap_phrase = " ".join(tail_words_chunk0)
    assert overlap_phrase in chunks[1]


def test_split_units_assigns_unique_chunk_ids_and_preserves_metadata() -> None:
    """[SP2-05.3 & SP2-05.4] Kiểm tra chunk_id, chunk_index tăng dần và kế thừa nguyên vẹn metadata."""
    doc_id = str(uuid.uuid4())
    page1_text = " ".join(
        [
            f"Điều {i}. Nội dung quy định chi tiết tại trang thứ nhất của tài liệu."
            for i in range(1, 12)
        ]
    )
    page2_text = " ".join(
        [
            f"Khoản {i}. Hướng dẫn thi hành chi tiết tại trang thứ hai của tài liệu."
            for i in range(1, 10)
        ]
    )

    units = [
        ExtractedUnit(
            text=page1_text,
            document_id=doc_id,
            filename="Luat_Lao_dong.pdf",
            page_number=1,
            source_type="pdf",
        ),
        ExtractedUnit(
            text=page2_text,
            document_id=doc_id,
            filename="Luat_Lao_dong.pdf",
            page_number=2,
            source_type="pdf",
        ),
    ]

    chunks = split_extracted_units(units, chunk_size=45, chunk_overlap=10)
    assert len(chunks) >= 4

    # Kiểm tra đánh số thứ tự chunk_index liên tục (0, 1, 2, ...) và chunk_id duy nhất
    seen_ids = set()
    for expected_idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == expected_idx
        assert chunk.chunk_id == f"{doc_id}_chunk_{expected_idx}"
        assert chunk.chunk_id not in seen_ids
        seen_ids.add(chunk.chunk_id)

        assert chunk.document_id == doc_id
        assert chunk.filename == "Luat_Lao_dong.pdf"
        assert chunk.source_type == "pdf"
        assert chunk.page_number in {1, 2}
        assert chunk.metadata["page_number"] == chunk.page_number
        assert chunk.token_count <= 45


def test_splitter_invalid_parameters_raise_value_error() -> None:
    """Kiểm tra kiểm soát tham số chunk_size và chunk_overlap không hợp lệ."""
    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=0, chunk_overlap=10)

    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=100, chunk_overlap=100)

