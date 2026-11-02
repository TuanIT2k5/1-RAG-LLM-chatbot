from pathlib import Path
import uuid

import pymupdf as fitz
import pytest

from app.core.exceptions import EmptyDocumentException, ExtractionFailedException
from app.services.document_processor import extract_pdf


def create_sample_pdf(
    pdf_path: Path,
    pages_text: list[str],
    password: str | None = None,
) -> Path:
    """Tạo tệp PDF thực tế bằng PyMuPDF phục vụ kiểm thử."""
    doc = fitz.open()
    for content in pages_text:
        page = doc.new_page()
        if content:
            page.insert_text((72, 72), content, fontsize=12)

    if password:
        doc.save(
            str(pdf_path),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw=password,
            user_pw=password,
        )
    else:
        doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_extract_pdf_preserves_exact_page_numbers_and_metadata(tmp_path: Path) -> None:
    """[SP2-02.2 & SP2-02.3] Kiểm tra trích xuất đúng nội dung và số trang bắt đầu từ 1."""
    pdf_file = create_sample_pdf(
        tmp_path / "bo_luat_test.pdf",
        [
            "Dieu 1. Pham vi dieu chinh tai trang 1.",
            "",  # Trang 2 để trống
            "Dieu 113. Nghi hang nam tai trang 3.",
        ],
    )
    doc_id = uuid.uuid4()

    results = extract_pdf(
        file_path=pdf_file,
        document_id=doc_id,
        filename="Bo_luat_2019.pdf",
    )

    # Trang 2 trống nên chỉ trả về trang 1 và trang 3 với page_number chính xác
    assert len(results) == 2

    assert results[0].page_number == 1
    assert "Dieu 1. Pham vi dieu chinh" in results[0].text
    assert results[0].filename == "Bo_luat_2019.pdf"
    assert results[0].document_id == str(doc_id)

    assert results[1].page_number == 3
    assert "Dieu 113. Nghi hang nam" in results[1].text
    assert results[1]["page_number"] == 3
    assert results[1].to_dict()["filename"] == "Bo_luat_2019.pdf"


def test_extract_pdf_corrupted_or_encrypted_raises_extraction_failed(
    tmp_path: Path,
) -> None:
    """[SP2-02.1] Tệp PDF hỏng cấu trúc hoặc cài mật khẩu phải trả về EXTRACTION_FAILED."""
    # 1. Tệp hỏng cấu trúc
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"%PDF-1.7\nInvalid corrupted binary data")

    with pytest.raises(ExtractionFailedException) as exc_corrupt:
        extract_pdf(corrupted_pdf, document_id=uuid.uuid4())
    assert exc_corrupt.value.error_code == "EXTRACTION_FAILED"

    # 2. Tệp khóa mật khẩu
    encrypted_pdf = create_sample_pdf(
        tmp_path / "locked.pdf",
        ["Secret page content"],
        password="secret_password_123",
    )
    with pytest.raises(ExtractionFailedException) as exc_locked:
        extract_pdf(encrypted_pdf, document_id=uuid.uuid4())
    assert exc_locked.value.error_code == "EXTRACTION_FAILED"


def test_extract_pdf_scanned_or_blank_raises_empty_document(tmp_path: Path) -> None:
    """[SP2-02.4 & TC-05] Tệp PDF chỉ chứa ảnh/trang trắng không có chữ trả về EMPTY_DOCUMENT."""
    blank_pdf = create_sample_pdf(tmp_path / "scanned_no_text.pdf", ["", "   "])

    with pytest.raises(EmptyDocumentException) as exc_empty:
        extract_pdf(
            file_path=blank_pdf,
            document_id=uuid.uuid4(),
            filename="scanned_no_text.pdf",
        )
    assert exc_empty.value.error_code == "EMPTY_DOCUMENT"
    assert exc_empty.value.details.get("flag") == "EMPTY_DOCUMENT"

