from pathlib import Path
import uuid

import docx
import pymupdf as fitz
import pytest

from app.core.exceptions import EmptyDocumentException, ExtractionFailedException
from app.services.document_processor import extract_document, extract_docx, extract_pdf


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
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"%PDF-1.7\nInvalid corrupted binary data")

    with pytest.raises(ExtractionFailedException) as exc_corrupt:
        extract_pdf(corrupted_pdf, document_id=uuid.uuid4())
    assert exc_corrupt.value.error_code == "EXTRACTION_FAILED"

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


def test_extract_docx_paragraphs_headings_and_tables(tmp_path: Path) -> None:
    """[SP2-03.1 -> SP2-03.4 & TC-02] Trích xuất DOCX có Heading, đoạn văn và bảng biểu."""
    docx_file = tmp_path / "noi_quy_cong_ty.docx"
    word_doc = docx.Document()

    # Mục 1: Heading 1 + đoạn văn
    word_doc.add_heading("Chương 1: Quy định chung", level=1)
    word_doc.add_paragraph("Thời gian làm việc từ thứ Hai đến thứ Sáu hằng tuần.")

    # Mục 2: Heading 2 + bảng biểu + đoạn văn
    word_doc.add_heading("Điều 2: Chế độ nghỉ phép", level=2)
    table = word_doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Thâm niên"
    table.cell(0, 1).text = "Số ngày phép"
    table.cell(1, 0).text = "Đủ 12 tháng"
    table.cell(1, 1).text = "12 ngày"

    word_doc.add_paragraph("Nhân viên đăng ký nghỉ phép trước ít nhất 02 ngày.")
    word_doc.save(str(docx_file))

    doc_id = uuid.uuid4()
    units = extract_docx(
        file_path=docx_file,
        document_id=doc_id,
        filename="Noi_quy_Cong_ty.docx",
    )

    assert len(units) == 5

    # Đoạn 1: Heading 1
    assert units[0].paragraph_index == 1
    assert units[0].section_title == "Chương 1: Quy định chung"
    assert units[0].filename == "Noi_quy_Cong_ty.docx"
    assert units[0].document_id == str(doc_id)
    assert units[0].source_type == "docx"

    # Đoạn 2: Kế thừa section_title từ Heading 1
    assert units[1].paragraph_index == 2
    assert units[1].section_title == "Chương 1: Quy định chung"
    assert "thứ Hai đến thứ Sáu" in units[1].text

    # Đoạn 3: Heading 2 cập nhật section_title mới
    assert units[2].paragraph_index == 3
    assert units[2].section_title == "Điều 2: Chế độ nghỉ phép"

    # Đoạn 4: Bảng biểu kế thừa section_title từ Heading 2
    assert units[3].paragraph_index == 4
    assert units[3].section_title == "Điều 2: Chế độ nghỉ phép"
    assert "Thâm niên | Số ngày phép" in units[3].text
    assert "Đủ 12 tháng | 12 ngày" in units[3].text

    # Đoạn 5: Đoạn văn sau bảng
    assert units[4].paragraph_index == 5
    assert units[4].section_title == "Điều 2: Chế độ nghỉ phép"
    assert "trước ít nhất 02 ngày" in units[4].text


def test_extract_docx_empty_and_corrupted(tmp_path: Path) -> None:
    """Kiểm tra tệp DOCX rỗng (EMPTY_DOCUMENT) và tệp DOCX hỏng (EXTRACTION_FAILED)."""
    # 1. Tệp DOCX trắng không có chữ
    empty_docx = tmp_path / "empty.docx"
    doc = docx.Document()
    doc.add_paragraph("   ")
    doc.save(str(empty_docx))

    with pytest.raises(EmptyDocumentException) as exc_empty:
        extract_document(empty_docx, document_id=uuid.uuid4())
    assert exc_empty.value.error_code == "EMPTY_DOCUMENT"

    # 2. Tệp DOCX hỏng cấu trúc
    bad_docx = tmp_path / "corrupted.docx"
    bad_docx.write_bytes(b"PK\x03\x04 corrupted zip content")

    with pytest.raises(ExtractionFailedException) as exc_bad:
        extract_docx(bad_docx, document_id=uuid.uuid4())
    assert exc_bad.value.error_code == "EXTRACTION_FAILED"
