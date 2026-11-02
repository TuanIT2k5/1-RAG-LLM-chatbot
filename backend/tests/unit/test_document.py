import io
from pathlib import Path
from typing import Dict
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    EmptyDocumentException,
    FileTooLargeException,
    InvalidFileException,
)
from app.database.connection import Base
from app.services.document_processor import extract_document, extract_docx, extract_pdf
from app.services.text_splitter import (
    RecursiveTextSplitter,
    count_tokens,
    split_extracted_units,
)
from app.utils.file_validator import (
    DOCX_MIME,
    PDF_MIME,
    save_upload_file_stream,
    validate_and_register_document,
)


def test_sp2_06_1_sample_fixtures_generated(sample_files: Dict[str, Path]) -> None:
    """
    [SP2-06.1] Xác nhận bộ 4 tệp mẫu kiểm thử (PDF tiếng Việt 25 trang, DOCX có tiêu đề/bảng,
    tệp PDF rỗng/scan, tệp sai định dạng) đều tồn tại và sẵn sàng.
    """
    assert sample_files["pdf_25_pages"].exists()
    assert sample_files["docx_with_table"].exists()
    assert sample_files["empty_pdf"].exists()
    assert sample_files["invalid_file"].exists()


def test_sp2_06_2_pdf_25_pages_exact_page_number_matching(
    sample_files: Dict[str, Path],
) -> None:
    """
    [SP2-06.2 & Sprint 2 DoD] Kiểm tra trích xuất tệp PDF tiếng Việt 25 trang (trên 20 trang):
    Số trang trích xuất (page_number) phải khớp tuyệt đối 100% với vị trí trang thực tế của văn bản.
    """
    doc_id = uuid.uuid4()
    pdf_path = sample_files["pdf_25_pages"]

    pages = extract_pdf(
        file_path=pdf_path,
        document_id=doc_id,
        filename="Bo_luat_Lao_dong_25_trang.pdf",
    )

    assert len(pages) == 25
    for idx, page_unit in enumerate(pages, start=1):
        assert page_unit.page_number == idx
        assert f"TRANG SỐ {idx}" in page_unit.text
        assert f"Điều {idx}." in page_unit.text
        assert page_unit.filename == "Bo_luat_Lao_dong_25_trang.pdf"
        assert page_unit.document_id == str(doc_id)


def test_sp2_06_3_chunk_length_overlap_and_metadata_on_25page_pdf_and_docx(
    sample_files: Dict[str, Path],
    tmp_path: Path,
) -> None:
    """
    [SP2-06.3 & Sprint 2 DoD] Tải thử 1 tệp PDF (25 trang) và 1 tệp DOCX tiếng Việt:
    - Tách thành các Chunk rõ ràng, độ dài nằm trong ngưỡng cấu hình (<= chunk_size).
    - Phần văn bản chồng lấp (overlap) hoạt động đúng, không bị đứt câu.
    - Mỗi Chunk đều lưu đúng tên tệp gốc, mã tài liệu và số trang / section_title.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with TestingSession() as db:
        # 1. Luồng đầy đủ cho tệp PDF 25 trang
        with sample_files["pdf_25_pages"].open("rb") as f_pdf:
            pdf_doc_record = validate_and_register_document(
                db=db,
                upload_file=f_pdf,
                filename="Bo_luat_Lao_dong_25_trang.pdf",
                content_type=PDF_MIME,
                upload_dir=tmp_path,
            )

        pdf_units = extract_document(
            file_path=pdf_doc_record.storage_path,
            document_id=pdf_doc_record.id,
            filename=pdf_doc_record.filename,
        )
        pdf_chunks = split_extracted_units(
            pdf_units,
            chunk_size=45,
            chunk_overlap=12,
        )

        # Có 25 trang, mỗi trang > 45 tokens nên phải sinh ra > 25 Chunks
        assert len(pdf_chunks) >= 25
        for expected_idx, chunk in enumerate(pdf_chunks):
            assert chunk.chunk_index == expected_idx
            assert chunk.chunk_id == f"{pdf_doc_record.id}_chunk_{expected_idx}"
            assert chunk.token_count <= 45
            assert chunk.document_id == str(pdf_doc_record.id)
            assert chunk.filename == "Bo_luat_Lao_dong_25_trang.pdf"
            assert chunk.page_number is not None
            assert 1 <= chunk.page_number <= 25
            # Dòng đánh số trang đơn lẻ "- X -" đã được bộ lọc làm sạch
            assert f"- {chunk.page_number} -" not in chunk.text

        # Kiểm tra 2 Chunk cùng 1 trang có phần văn bản chồng lấp (overlap)
        page1_chunks = [c for c in pdf_chunks if c.page_number == 1]
        assert len(page1_chunks) >= 2
        tail_words = page1_chunks[0].text.split()[-4:]
        assert " ".join(tail_words) in page1_chunks[1].text

        # 2. Luồng đầy đủ cho tệp DOCX tiếng Việt có tiêu đề & bảng biểu
        with sample_files["docx_with_table"].open("rb") as f_docx:
            docx_record = validate_and_register_document(
                db=db,
                upload_file=f_docx,
                filename="Noi_quy_Lao_dong.docx",
                content_type=DOCX_MIME,
                upload_dir=tmp_path,
            )

        docx_units = extract_docx(
            file_path=docx_record.storage_path,
            document_id=docx_record.id,
            filename=docx_record.filename,
        )
        docx_chunks = RecursiveTextSplitter(
            chunk_size=400,
            chunk_overlap=60,
        ).split_units(docx_units)

        assert len(docx_chunks) >= 4
        combined_docx_text = "\n".join(c.text for c in docx_chunks)
        assert "Chương 1: Quy định chung về Quản lý Nhân sự" in combined_docx_text
        assert "Nhân viên văn phòng | Điều kiện bình thường | 12 ngày làm việc" in combined_docx_text
        assert all(c.filename == "Noi_quy_Lao_dong.docx" for c in docx_chunks)
        assert all(c.document_id == str(docx_record.id) for c in docx_chunks)
        assert all(c.paragraph_index is not None for c in docx_chunks)


def test_sp2_06_4_error_codes_for_oversized_empty_and_invalid_files(
    sample_files: Dict[str, Path],
    tmp_path: Path,
) -> None:
    """
    [SP2-06.4] Xác nhận hệ thống bắt đúng mã lỗi chuẩn khi đưa vào:
    - Tệp sai định dạng / giả mạo -> INVALID_FILE (400)
    - Tệp vượt dung lượng -> FILE_TOO_LARGE (413)
    - Tệp không có chữ (PDF scan / rỗng) -> EMPTY_DOCUMENT (422)
    """
    # 1. Tệp giả mạo .exe đổi đuôi .pdf -> INVALID_FILE
    with sample_files["invalid_file"].open("rb") as f_bad:
        with pytest.raises(InvalidFileException) as exc_invalid:
            save_upload_file_stream(
                file_obj=f_bad,
                filename="sample_invalid_spoofed.pdf",
                content_type=PDF_MIME,
                upload_dir=tmp_path,
            )
    assert exc_invalid.value.error_code == "INVALID_FILE"
    assert exc_invalid.value.status_code == 400

    # 2. Tệp vượt dung lượng cho phép -> FILE_TOO_LARGE
    oversized_stream = io.BytesIO(b"%PDF-1.7\n" + b"X" * (2 * 1024 * 1024))
    with pytest.raises(FileTooLargeException) as exc_large:
        save_upload_file_stream(
            file_obj=oversized_stream,
            filename="oversized.pdf",
            content_type=PDF_MIME,
            max_size_bytes=1 * 1024 * 1024,  # Giới hạn 1MB
            upload_dir=tmp_path,
        )
    assert exc_large.value.error_code == "FILE_TOO_LARGE"
    assert exc_large.value.status_code == 413

    # 3. Tệp PDF ảnh scan không có lớp văn bản -> EMPTY_DOCUMENT
    with pytest.raises(EmptyDocumentException) as exc_empty:
        extract_pdf(
            file_path=sample_files["empty_pdf"],
            document_id=uuid.uuid4(),
            filename="sample_empty_scanned.pdf",
        )
    assert exc_empty.value.error_code == "EMPTY_DOCUMENT"
    assert exc_empty.value.status_code == 422

